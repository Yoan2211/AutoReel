from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ResolveBridgeConfig
from .errors import BridgeNotFoundError, BridgeUnavailableError, ResolveBuilderError


PROTOCOL_VERSION = "1.0"
MAX_REQUEST_BYTES = 1_048_576


def _canonical_request(request: dict) -> bytes:
    unsigned = {k: v for k, v in request.items() if k != "signature"}
    return json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sign_request(token: str, request: dict) -> str:
    return hmac.new(
        token.encode("utf-8"),
        _canonical_request(request),
        hashlib.sha256,
    ).hexdigest()


def _load_private_config(config: ResolveBridgeConfig) -> dict:
    path = config.config_path.expanduser()
    if not path.is_file():
        raise BridgeNotFoundError(f"bridge.json not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResolveBuilderError(f"Invalid bridge configuration: {path}") from exc

    host = raw.get("host", "127.0.0.1")
    port = raw.get("port", 49632)
    token = raw.get("token")

    if host not in {"127.0.0.1", "localhost"}:
        raise ResolveBuilderError(
            f"Refusing non-loopback Resolve bridge host: {host!r}"
        )
    if type(port) is not int or not (1024 <= port <= 65535):
        raise ResolveBuilderError(f"Invalid Resolve bridge port: {port!r}")
    if not isinstance(token, str) or len(token) < 43:
        raise ResolveBuilderError(
            "Resolve bridge authentication token is missing or invalid"
        )

    return {
        "host": host,
        "port": port,
        "token": token,
        "media_roots": raw.get("media_roots"),
        "output_roots": raw.get("output_roots"),
    }


def read_bridge_config(config: ResolveBridgeConfig) -> dict:
    """Return only non-secret configuration fields."""
    raw = _load_private_config(config)
    return {
        "config_path": str(config.config_path.expanduser().resolve()),
        "host": raw["host"],
        "port": raw["port"],
        "has_token": True,
        "media_roots": raw.get("media_roots"),
        "output_roots": raw.get("output_roots"),
    }


class BridgeTransport:
    def __init__(self, config: dict, timeout: float) -> None:
        self.host = config["host"]
        self.port = int(config["port"])
        self._token = config["token"]
        self.timeout = float(timeout)
        self._lock = threading.RLock()

    def request(self, operation: str, arguments: dict) -> Any:
        payload = {
            "protocol": PROTOCOL_VERSION,
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "nonce": secrets.token_urlsafe(24),
            "operation": operation,
            "arguments": arguments,
        }
        payload["signature"] = _sign_request(self._token, payload)

        line = (
            json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n"
        ).encode("utf-8")
        if len(line) > MAX_REQUEST_BYTES:
            raise ResolveBuilderError("Resolve bridge request is too large")

        with self._lock:
            try:
                with socket.create_connection(
                    (self.host, self.port), timeout=self.timeout
                ) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendall(line)
                    raw = sock.makefile("rb").readline(MAX_REQUEST_BYTES + 1)
            except (TimeoutError, socket.timeout) as exc:
                raise BridgeUnavailableError(
                    "Resolve bridge timed out. Check that Resolve has no modal "
                    "dialog open and that Workspace > Scripts > resolve_bridge "
                    "is running."
                ) from exc
            except OSError as exc:
                raise BridgeUnavailableError(
                    f"Cannot reach the in-Resolve bridge on "
                    f"{self.host}:{self.port}. In Resolve, run "
                    f"Workspace > Scripts > resolve_bridge. ({exc})"
                ) from exc

        if not raw:
            raise BridgeUnavailableError("Resolve bridge closed without replying")

        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResolveBuilderError("Resolve bridge returned invalid JSON") from exc

        if not isinstance(response, dict):
            raise ResolveBuilderError("Resolve bridge returned a non-object")
        if response.get("id") != payload["id"]:
            raise ResolveBuilderError("Resolve bridge response id does not match")
        if response.get("ok") is not True:
            error = response.get("error") or {}
            code = str(error.get("code", "bridge_error"))
            message = str(error.get("message", "Resolve bridge refused the call"))
            raise ResolveBuilderError(f"{code}: {message}")

        return response.get("result")


def _encode_argument(value: Any) -> Any:
    if isinstance(value, BridgeProxy):
        return {"__handle__": value._handle}
    if isinstance(value, dict):
        return {k: _encode_argument(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_argument(v) for v in value]
    return value


def _decode_value(transport: BridgeTransport, value: Any) -> Any:
    if isinstance(value, dict):
        handle = value.get("__handle__")
        if handle is not None:
            return BridgeProxy(
                transport,
                str(handle),
                type_name=value.get("__type__"),
                shape=value.get("__shape__"),
            )
        return {k: _decode_value(transport, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(transport, item) for item in value]
    return value


class _BoundMethod:
    def __init__(self, proxy: "BridgeProxy", name: str) -> None:
        self._proxy = proxy
        self._name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs:
            raise TypeError(
                "Resolve bridge calls must use positional arguments only"
            )
        result = self._proxy._transport.request(
            "call",
            {
                "target": self._proxy._handle,
                "method": self._name,
                "args": [_encode_argument(arg) for arg in args],
            },
        )
        if isinstance(result, dict) and "value" in result:
            return _decode_value(self._proxy._transport, result.get("value"))
        return _decode_value(self._proxy._transport, result)


class BridgeProxy:
    def __init__(
        self,
        transport: BridgeTransport,
        handle: str,
        *,
        type_name: str | None = None,
        shape: str | None = None,
    ) -> None:
        self._transport = transport
        self._handle = handle
        self._type_name = type_name
        self._shape = shape

    def methods(self) -> set[str]:
        result = self._transport.request(
            "list_methods",
            {"target": self._handle},
        )
        if isinstance(result, dict):
            methods = result.get("methods", [])
        elif isinstance(result, list):
            methods = result
        else:
            methods = []
        return {str(name) for name in methods}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        # Keep capability checks truthful instead of pretending every method exists.
        methods = self.methods()
        if name not in methods:
            raise AttributeError(
                f"{self._type_name or 'Resolve object'} has no method {name!r}"
            )
        return _BoundMethod(self, name)


@dataclass
class BridgeSession:
    resolve: BridgeProxy
    transport: BridgeTransport
    config: ResolveBridgeConfig

    def health(self) -> dict:
        value = self.transport.request("health", {})
        return value if isinstance(value, dict) else {"connected": True}

    @staticmethod
    def has_method(obj: Any, name: str) -> bool:
        if obj is None:
            return False
        if isinstance(obj, BridgeProxy):
            try:
                return name in obj.methods()
            except Exception:
                return False
        try:
            return callable(getattr(obj, name))
        except Exception:
            return False

    @staticmethod
    def safe_call(obj: Any, name: str, *args: Any) -> Any:
        if obj is None:
            return None
        try:
            fn = getattr(obj, name)
            if not callable(fn):
                return None
            return fn(*args)
        except Exception:
            return None


def connect_bridge(config: ResolveBridgeConfig | None = None) -> BridgeSession:
    config = config or ResolveBridgeConfig.default()
    private = _load_private_config(config)
    transport = BridgeTransport(private, timeout=config.timeout_seconds)
    resolve = BridgeProxy(
        transport,
        "resolve",
        type_name="Resolve",
        shape="resolve",
    )

    # Prove the bridge is actually alive before the probe proceeds.
    try:
        health = transport.request("health", {})
    except (ResolveBuilderError, BridgeUnavailableError):
        raise
    except Exception as exc:
        raise BridgeUnavailableError(
            f"Unable to connect to Resolve bridge: {exc}"
        ) from exc

    if not isinstance(health, dict) or health.get("connected") is not True:
        raise BridgeUnavailableError("Resolve bridge health check failed")

    return BridgeSession(
        resolve=resolve,
        transport=transport,
        config=config,
    )
