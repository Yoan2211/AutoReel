from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def fail(message: str, code: int = 1):
    print(f"\nERREUR: {message}")
    input("\nAppuie sur Entrée pour fermer...")
    raise SystemExit(code)


def find_build_lua() -> Path:
    preferred = ROOT / "projects" / "anemie" / "m11_resolve_build" / "autoreel_m11_build.lua"
    if preferred.is_file():
        return preferred

    candidates = list((ROOT / "projects").glob("*/m11_resolve_build/autoreel_m11_build.lua"))
    if not candidates:
        fail("Aucun autoreel_m11_build.lua n'a été trouvé dans projects\\*\\m11_resolve_build.")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def decode_lua_string(value: str) -> str:
    # Generated AutoReel paths currently need only standard backslash decoding.
    return value.replace("\\\\", "\\")


def encode_lua_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def extract_source_path(text: str) -> Path:
    match = re.search(r'\["physical_path"\]\s*=\s*"([^"]+)"', text)
    if not match:
        fail("Impossible de trouver physical_path dans le script M11.")
    path = Path(decode_lua_string(match.group(1)))
    if not path.is_file():
        fail(f"Vidéo source introuvable:\n{path}")
    return path


def ffprobe_json(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,pix_fmt,width,height,color_primaries,color_transfer,color_space",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        fail("ffprobe est introuvable dans le PATH.")
    except subprocess.CalledProcessError as exc:
        fail("ffprobe a échoué:\n" + (exc.stderr or exc.stdout or "erreur inconnue"))
    return json.loads(result.stdout)


def duration_seconds(probe: dict) -> float:
    try:
        return float(probe.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def video_stream(probe: dict) -> dict | None:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def print_probe(label: str, probe: dict):
    v = video_stream(probe)
    if not v:
        print(f"{label}: aucune piste vidéo")
        return
    print(
        f"{label}: codec={v.get('codec_name')} "
        f"pix_fmt={v.get('pix_fmt')} "
        f"{v.get('width')}x{v.get('height')} "
        f"transfer={v.get('color_transfer')}"
    )


def run_ffmpeg_with_progress(source: Path, output: Path, probe: dict):
    duration = duration_seconds(probe)
    v = video_stream(probe) or {}

    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "dnxhd",
        "-profile:v", "dnxhr_hqx",
        "-pix_fmt", "yuv422p10le",
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        "-metadata:s:v:0", "rotate=0",
    ]

    # Preserve known color tags when FFmpeg reported them.
    mapping = (
        ("color_primaries", "-color_primaries"),
        ("color_transfer", "-color_trc"),
        ("color_space", "-colorspace"),
    )
    for key, option in mapping:
        value = v.get(key)
        if value and value not in {"unknown", "reserved"}:
            cmd += [option, str(value)]

    cmd += [
        "-progress", "pipe:1",
        "-nostats",
        str(output),
    ]

    print("\nConversion Resolve-compatible")
    print("Codec de travail: DNxHR HQX 10 bits + PCM 48 kHz")
    print("La vidéo originale n'est pas modifiée.\n")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        fail("ffmpeg est introuvable dans le PATH.")

    last_pct = -1
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.strip()
        if line.startswith("out_time_us=") and duration > 0:
            try:
                out_us = int(line.split("=", 1)[1])
                pct = max(0, min(100, int((out_us / 1_000_000) / duration * 100)))
                if pct != last_pct:
                    print(f"\rConversion : {pct:3d} %", end="", flush=True)
                    last_pct = pct
            except ValueError:
                pass
        elif line == "progress=end":
            print("\rConversion : 100 %", flush=True)

    code = proc.wait()
    if code != 0:
        if output.exists():
            output.unlink(missing_ok=True)
        fail(f"FFmpeg a échoué (code {code}).")


def patch_lua(lua_path: Path, original: Path, replacement: Path) -> Path:
    text = lua_path.read_text(encoding="utf-8")
    old = encode_lua_string(str(original))
    new = encode_lua_string(str(replacement))

    count = text.count(old)
    if count == 0:
        fail("Le chemin de la source n'a pas été retrouvé dans le Lua généré.")

    patched = text.replace(old, new)
    target = lua_path.with_name("autoreel_m11_build_VIDEO_FIX.lua")
    target.write_text(patched, encoding="utf-8")
    print(f"\nLua corrigé: {target}")
    print(f"Occurrences remplacées: {count}")
    return target


def main():
    print("=" * 72)
    print("AUTOREEL M11 - CORRECTIF VIDEO RESOLVE")
    print("=" * 72)

    lua_path = find_build_lua()
    text = lua_path.read_text(encoding="utf-8")
    source = extract_source_path(text)

    print(f"Script M11 : {lua_path}")
    print(f"Source     : {source}")

    source_probe = ffprobe_json(source)
    print_probe("Source", source_probe)

    build_dir = lua_path.parent
    compatible = build_dir / "source_RESOLVE_DNXHR_HQX.mov"

    reuse = False
    if compatible.is_file() and compatible.stat().st_size > 0:
        try:
            existing_probe = ffprobe_json(compatible)
            if video_stream(existing_probe):
                reuse = True
                print(f"\n[OK] Média Resolve-compatible déjà présent : {compatible}")
                print_probe("Compatible", existing_probe)
        except Exception:
            reuse = False

    if not reuse:
        run_ffmpeg_with_progress(source, compatible, source_probe)
        compatible_probe = ffprobe_json(compatible)
        if not video_stream(compatible_probe):
            compatible.unlink(missing_ok=True)
            fail("La conversion a terminé mais le fichier de sortie n'a pas de piste vidéo.")
        print_probe("Compatible", compatible_probe)

    patched = patch_lua(lua_path, source, compatible)

    command = f"dofile([[{patched}]])"

    print("\n" + "=" * 72)
    print("PRÊT")
    print("=" * 72)
    print("1. Ouvre DaVinci Resolve.")
    print("2. Workspace > Console > Lua")
    print("3. Colle cette ligne :\n")
    print(command)
    print("\nLe script créera une NOUVELLE timeline AutoReel.")
    print("Il ne supprime pas la timeline audio-only existante.")

    input("\nAppuie sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
