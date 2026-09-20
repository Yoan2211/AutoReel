from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolveBridgeConfig:
    """Locations used by the already-installed free Resolve bridge."""

    install_root: Path
    config_path: Path
    timeout_seconds: float = 8.0

    @classmethod
    def default(cls) -> "ResolveBridgeConfig":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            install_root = Path(local_appdata) / "davinci-resolve-mcp"
        else:
            install_root = Path.home() / "AppData" / "Local" / "davinci-resolve-mcp"

        config_override = os.environ.get("DAVINCI_RESOLVE_BRIDGE_CONFIG")
        config_path = (
            Path(config_override).expanduser()
            if config_override
            else Path.home() / ".config" / "davinci-resolve-mcp" / "bridge.json"
        )
        return cls(
            install_root=install_root,
            config_path=config_path,
            timeout_seconds=8.0,
        )
