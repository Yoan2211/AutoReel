from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def log(message: str) -> None:
    print(message, flush=True)


def decode_lua(value: str) -> str:
    return value.replace("\\\\", "\\")


def encode_lua(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def find_lua(project: Path) -> Path:
    preferred = project / "m11_resolve_build" / "autoreel_m11_build.lua"
    if preferred.is_file():
        return preferred
    candidates = list(project.glob("m11_resolve_build*/autoreel_m11_build*.lua"))
    if not candidates:
        raise FileNotFoundError("Aucun autoreel_m11_build.lua trouvé")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def first_source(text: str) -> Path | None:
    m = re.search(r'\["physical_path"\]\s*=\s*"([^"]+)"', text)
    return Path(decode_lua(m.group(1))) if m else None


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,pix_fmt",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def ensure_resolve_media(lua: Path, text: str) -> str:
    source = first_source(text)
    if source is None or not source.is_file():
        log("[M11] Source non trouvée: conversion automatique ignorée.")
        return text

    meta = probe(source)
    video = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), {})
    codec = str(video.get("codec_name") or "").lower()
    pix = str(video.get("pix_fmt") or "").lower()
    needs = codec in {"hevc", "h265"} or "10le" in pix

    if not needs:
        log(f"[M11] Source OK: {codec} {pix}")
        return text

    target = lua.parent / "source_RESOLVE_DNXHR_HQX.mov"
    if not target.is_file() or target.stat().st_size == 0:
        duration = float(meta.get("format", {}).get("duration") or 0)
        cmd = [
            "ffmpeg", "-hide_banner", "-y", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "dnxhd", "-profile:v", "dnxhr_hqx", "-pix_fmt", "yuv422p10le",
            "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
            "-metadata:s:v:0", "rotate=0",
            "-progress", "pipe:1", "-nostats", str(target),
        ]
        log("[M11] Conversion DNxHR HQX...")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        assert proc.stdout is not None
        last = -1
        for line in proc.stdout:
            if line.startswith("out_time_us=") and duration > 0:
                try:
                    us = int(line.split("=", 1)[1])
                    pct = max(0, min(100, int(us / 1_000_000 / duration * 100)))
                    if pct != last:
                        log(f"[M11] Conversion: {pct}%")
                        last = pct
                except ValueError:
                    pass
        if proc.wait() != 0:
            raise RuntimeError("Conversion FFmpeg échouée")
        log("[M11] Conversion: 100%")

    return text.replace(encode_lua(str(source)), encode_lua(str(target)))


DYNAMIC_FUNCTION = r'''local AUTOREEL_SHOT_LENGTHS = {144, 180, 132, 168}
local AUTOREEL_ZOOMS = {1.00, 1.08, 1.13, 1.04, 1.10, 1.02}

local function autoreel_chunk_length(event_index, part_index)
    local index = ((event_index + part_index - 2) % #AUTOREEL_SHOT_LENGTHS) + 1
    return AUTOREEL_SHOT_LENGTHS[index]
end

local function autoreel_zoom(event_index, part_index)
    local index = ((event_index * 2 + part_index - 3) % #AUTOREEL_ZOOMS) + 1
    return AUTOREEL_ZOOMS[index]
end

local function place_track(media_pool, track_id, track_index, media_type)
    for event_index, event in ipairs(BUILD.tracks[track_id]) do
        local item, import_err = media_for_path(media_pool, event.physical_path)
        if item == nil then
            track_fail(track_id, event.id .. " import failed: " .. tostring(import_err))
        else
            local event_duration = event.record_end_frame - event.record_start_frame

            if track_id == "V1" or track_id == "A1" then
                local offset = 0
                local part_index = 1

                while offset < event_duration do
                    local wanted = autoreel_chunk_length(event_index, part_index)
                    local chunk = math.min(wanted, event_duration - offset)
                    local remaining = event_duration - (offset + chunk)
                    if remaining > 0 and remaining < 48 then
                        chunk = chunk + remaining
                    end

                    local clip_info = {
                        mediaPoolItem = item,
                        startFrame = event.source_start_frame + offset,
                        endFrame = event.source_start_frame + offset + chunk,
                        recordFrame = event.record_start_frame + offset,
                        trackIndex = track_index,
                        mediaType = media_type,
                    }
                    local timeline_item, append_err = append_one(media_pool, clip_info)

                    if timeline_item == nil then
                        track_fail(track_id, event.id .. " part " .. tostring(part_index)
                            .. " placement failed: " .. tostring(append_err))
                    else
                        if not verify_item_duration(timeline_item, chunk) then
                            track_fail(track_id, event.id .. " part " .. tostring(part_index)
                                .. " duration mismatch")
                        else
                            track_ok(track_id)
                        end

                        if track_id == "V1" then
                            local zoom = autoreel_zoom(event_index, part_index)
                            local okx = apply_static_property(timeline_item, "ZoomX", zoom)
                            local oky = apply_static_property(timeline_item, "ZoomY", zoom)
                            if not okx or not oky then unsupported("AUTOREEL_STATIC_PUNCH_IN") end
                        end
                    end

                    offset = offset + chunk
                    part_index = part_index + 1
                end
            else
                local expected_duration = event.record_end_frame - event.record_start_frame
                local clip_info = {
                    mediaPoolItem = item,
                    startFrame = event.source_start_frame,
                    endFrame = event.source_end_frame,
                    recordFrame = event.record_start_frame,
                    trackIndex = track_index,
                    mediaType = media_type,
                }
                local timeline_item, append_err = append_one(media_pool, clip_info)

                if timeline_item == nil then
                    track_fail(track_id, event.id .. " placement failed: " .. tostring(append_err))
                else
                    if not verify_item_duration(timeline_item, expected_duration) then
                        track_fail(track_id, event.id .. " duration mismatch after placement")
                    else
                        track_ok(track_id)
                    end

                    if track_id == "A2" then
                        apply_music_levels(timeline_item, event)
                    elseif track_id == "A3" and event.gain_db ~= nil then
                        local ok = apply_static_property(timeline_item, "Volume", event.gain_db)
                        if not ok then unsupported("SFX_GAIN") end
                    end
                end
            end
        end
    end
end

local function try_import_srt'''


def patch_dynamic(text: str) -> str:
    if "AUTOREEL_SHOT_LENGTHS" in text:
        return text
    pattern = re.compile(
        r'local function place_track\(media_pool, track_id, track_index, media_type\).*?'
        r'local function try_import_srt',
        re.S,
    )
    if not pattern.search(text):
        raise RuntimeError("Fonction place_track introuvable")
    return pattern.sub(DYNAMIC_FUNCTION, text, count=1)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: m11_dynamic_postprocess.py <project_dir>")

    project = Path(sys.argv[1]).resolve()
    lua = find_lua(project)
    log(f"[M11] Dynamic V3: {lua}")

    text = lua.read_text(encoding="utf-8")
    backup = lua.with_suffix(".lua.before_dynamic_v3")
    if not backup.exists():
        shutil.copy2(lua, backup)

    text = ensure_resolve_media(lua, text)
    text = patch_dynamic(text)
    lua.write_text(text, encoding="utf-8")

    log("[M11] Plans: environ 2.2-3.0 s")
    log("[M11] Punch-ins: 1.00 / 1.08 / 1.13 / 1.04 / 1.10 / 1.02")
    log("[M11] Script Lua dynamique prêt.")


if __name__ == "__main__":
    main()
