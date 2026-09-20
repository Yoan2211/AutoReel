from __future__ import annotations

from .lua_serialize import to_lua


LUA_RUNTIME = r"""
local BUILD = __BUILD_DATA__

local function log(msg)
    print("[AutoReel M11] " .. tostring(msg))
end

local function push(tbl, value)
    tbl[#tbl + 1] = value
end

local function safe_method(obj, name)
    if obj == nil then return nil end
    local ok, value = pcall(function() return obj[name] end)
    if ok and type(value) == "function" then return value end
    return nil
end

local function safe_call(obj, name, ...)
    local fn = safe_method(obj, name)
    if fn == nil then return nil, name .. " unavailable" end
    local args = {...}
    local ok, value = pcall(function() return fn(obj, unpack(args)) end)
    if not ok then return nil, tostring(value) end
    return value, nil
end

local function normalize_path(path)
    if path == nil then return nil end
    return string.lower(string.gsub(tostring(path), "/", "\\"))
end

local function json_escape(value)
    local s = tostring(value)
    s = string.gsub(s, "\\", "\\\\")
    s = string.gsub(s, '"', '\\"')
    s = string.gsub(s, "\r", "\\r")
    s = string.gsub(s, "\n", "\\n")
    s = string.gsub(s, "\t", "\\t")
    return s
end

local function is_array(t)
    if type(t) ~= "table" then return false end
    local count = 0
    local max = 0
    for k, _ in pairs(t) do
        if type(k) ~= "number" or k < 1 or math.floor(k) ~= k then
            return false
        end
        count = count + 1
        if k > max then max = k end
    end
    return count == max
end

local function json_encode(value)
    local kind = type(value)
    if value == nil then return "null" end
    if kind == "boolean" then return value and "true" or "false" end
    if kind == "number" then return tostring(value) end
    if kind == "string" then return '"' .. json_escape(value) .. '"' end
    if kind ~= "table" then return '"' .. json_escape(tostring(value)) .. '"' end

    if is_array(value) then
        local rows = {}
        for i = 1, #value do rows[#rows + 1] = json_encode(value[i]) end
        return "[" .. table.concat(rows, ",") .. "]"
    end

    local keys = {}
    for key, _ in pairs(value) do keys[#keys + 1] = tostring(key) end
    table.sort(keys)
    local rows = {}
    for _, key in ipairs(keys) do
        rows[#rows + 1] = '"' .. json_escape(key) .. '":' .. json_encode(value[key])
    end
    return "{" .. table.concat(rows, ",") .. "}"
end

local report = {
    schema_version = "1.0.0",
    module = {id = "M11", version = "1.0.0"},
    status = "FAILED",
    timeline_json_path = BUILD.timeline_json_path,
    timeline_json_sha256 = BUILD.timeline_json_sha256,
    resolve = {},
    tracks = {
        V1={requested_events=#BUILD.tracks.V1, applied_events=0, failed_events=0},
        V2={requested_events=#BUILD.tracks.V2, applied_events=0, failed_events=0},
        V3={requested_events=#BUILD.tracks.V3, applied_events=0, failed_events=0},
        A1={requested_events=#BUILD.tracks.A1, applied_events=0, failed_events=0},
        A2={requested_events=#BUILD.tracks.A2, applied_events=0, failed_events=0},
        A3={requested_events=#BUILD.tracks.A3, applied_events=0, failed_events=0},
    },
    capabilities = {},
    unsupported_features = {},
    warnings = {},
    errors = {},
}

local function unsupported(name)
    for _, value in ipairs(report.unsupported_features) do
        if value == name then return end
    end
    push(report.unsupported_features, name)
end

local function warning(msg)
    push(report.warnings, tostring(msg))
    log("WARNING: " .. tostring(msg))
end

local function fail(msg)
    push(report.errors, tostring(msg))
    log("ERROR: " .. tostring(msg))
end

local function track_ok(track_id)
    report.tracks[track_id].applied_events = report.tracks[track_id].applied_events + 1
end

local function track_fail(track_id, msg)
    report.tracks[track_id].failed_events = report.tracks[track_id].failed_events + 1
    warning(track_id .. ": " .. tostring(msg))
end

local function acquire_resolve()
    if app ~= nil and type(app.GetResolve) == "function" then
        local ok, r = pcall(function() return app:GetResolve() end)
        if ok and r ~= nil then return r end
    end
    if resolve ~= nil then return resolve end
    return nil
end

local function find_media_in_folder(folder, target)
    if folder == nil then return nil end
    local clips = safe_call(folder, "GetClipList")
    if type(clips) == "table" then
        for _, clip in ipairs(clips) do
            local props = safe_call(clip, "GetClipProperty")
            if type(props) == "table" then
                local raw = props["File Path"] or props["FilePath"]
                if raw ~= nil and normalize_path(raw) == target then
                    return clip
                end
            end
        end
    end
    local subs = safe_call(folder, "GetSubFolderList")
    if type(subs) == "table" then
        for _, sub in ipairs(subs) do
            local found = find_media_in_folder(sub, target)
            if found ~= nil then return found end
        end
    end
    return nil
end

local media_cache = {}
local function media_for_path(media_pool, path)
    local key = normalize_path(path)
    if media_cache[key] ~= nil then return media_cache[key] end

    local root = safe_call(media_pool, "GetRootFolder")
    local existing = find_media_in_folder(root, key)
    if existing ~= nil then
        media_cache[key] = existing
        return existing
    end

    local imported, err = safe_call(media_pool, "ImportMedia", {path})
    if err ~= nil or type(imported) ~= "table" or imported[1] == nil then
        return nil, err or "ImportMedia returned no MediaPoolItem"
    end
    media_cache[key] = imported[1]
    return imported[1]
end

local function unique_timeline_name(project, base)
    local used = {}
    local count = safe_call(project, "GetTimelineCount") or 0
    for i = 1, tonumber(count) or 0 do
        local tl = safe_call(project, "GetTimelineByIndex", i)
        if tl ~= nil then
            local name = safe_call(tl, "GetName")
            if name ~= nil then used[tostring(name)] = true end
        end
    end
    if not used[base] then return base end
    local n = 1
    while true do
        local candidate = string.format("%s_%03d", base, n)
        if not used[candidate] then return candidate end
        n = n + 1
    end
end

local function ensure_tracks(timeline)
    while (safe_call(timeline, "GetTrackCount", "video") or 0) < 2 do
        local ok = safe_call(timeline, "AddTrack", "video")
        if ok ~= true then return false, "cannot create V2" end
    end
    while (safe_call(timeline, "GetTrackCount", "audio") or 0) < 3 do
        local ok = safe_call(timeline, "AddTrack", "audio", "stereo")
        if ok ~= true then return false, "cannot create A2/A3" end
    end
    if #BUILD.tracks.V3 > 0 and (safe_call(timeline, "GetTrackCount", "subtitle") or 0) < 1 then
        local ok = safe_call(timeline, "AddTrack", "subtitle")
        if ok ~= true then
            unsupported("SUBTITLE_TRACK_CREATION")
        end
    end
    return true, nil
end

local function append_one(media_pool, info)
    local result, err = safe_call(media_pool, "AppendToTimeline", {info})
    if err ~= nil then return nil, err end
    if type(result) ~= "table" or result[1] == nil then
        return nil, "AppendToTimeline returned no TimelineItem"
    end
    return result[1], nil
end

local function verify_item_duration(item, expected)
    local duration = safe_call(item, "GetDuration")
    if duration == nil then return true end
    local actual = tonumber(duration)
    if actual == nil then return true end
    return math.abs(actual - expected) <= 1
end

local function apply_static_property(item, key, value)
    local ok, err = safe_call(item, "SetProperty", key, value)
    return ok == true, err
end

local function try_add_keyframe(item, key, frame, value)
    local fn = safe_method(item, "AddKeyframe")
    if fn == nil then return false, "AddKeyframe unavailable" end
    local ok, result = pcall(function() return fn(item, key, frame, value) end)
    if not ok or result ~= true then
        return false, ok and "AddKeyframe returned false" or tostring(result)
    end
    return true, nil
end

local function autocam_for_item(item, event)
    local keys = event.camera_keyframes or {}
    if #keys == 0 then return true end

    local first = keys[1]
    local dynamic = #keys > 1
    local dynamic_ok = true

    if dynamic and safe_method(item, "AddKeyframe") ~= nil then
        for _, kf in ipairs(keys) do
            local z1 = try_add_keyframe(item, "ZoomX", kf.clip_offset_frame, kf.zoom)
            local z2 = try_add_keyframe(item, "ZoomY", kf.clip_offset_frame, kf.zoom)
            if not z1 or not z2 then dynamic_ok = false break end
        end
    else
        dynamic_ok = false
    end

    if not dynamic_ok then
        apply_static_property(item, "ZoomX", first.zoom)
        apply_static_property(item, "ZoomY", first.zoom)
        if dynamic then unsupported("AUTOCAM_DYNAMIC_ZOOM") end
    end

    if math.abs((first.center_x or 0.5) - 0.5) > 0.0001
        or math.abs((first.center_y or 0.5) - 0.5) > 0.0001 then
        unsupported("AUTOCAM_CENTER_PAN_TILT_CALIBRATION")
    end
    return true
end

local function apply_music_levels(item, event)
    local levels = event.level_regions or {}
    if #levels == 0 then return end
    local first = levels[1]
    apply_static_property(item, "Volume", first.gain_db)

    if #levels > 1 then
        local all_ok = true
        for _, level in ipairs(levels) do
            local ok = try_add_keyframe(item, "Volume", level.clip_offset_frame, level.gain_db)
            if not ok then all_ok = false break end
        end
        if not all_ok then unsupported("MUSIC_LEVEL_AUTOMATION") end
    end
    if (event.fade_in_us or 0) > 0 or (event.fade_out_us or 0) > 0 then
        unsupported("MUSIC_FADES")
    end
end

local function place_track(media_pool, track_id, track_index, media_type)
    for _, event in ipairs(BUILD.tracks[track_id]) do
        local item, import_err = media_for_path(media_pool, event.physical_path)
        if item == nil then
            track_fail(track_id, event.id .. " import failed: " .. tostring(import_err))
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

                if track_id == "V1" then
                    autocam_for_item(timeline_item, event)
                elseif track_id == "A2" then
                    apply_music_levels(timeline_item, event)
                elseif track_id == "A3" and event.gain_db ~= nil then
                    local ok = apply_static_property(timeline_item, "Volume", event.gain_db)
                    if not ok then unsupported("SFX_GAIN") end
                end
            end
        end
    end
end

local function try_import_srt(media_pool)
    if #BUILD.tracks.V3 == 0 then return end
    local imported, err = safe_call(media_pool, "ImportMedia", {BUILD.srt_path})
    if err ~= nil or type(imported) ~= "table" or imported[1] == nil then
        warning("SRT could not be imported into Media Pool")
        unsupported("CAPTION_SRT_IMPORT")
        return
    end
    unsupported("CAPTION_TIMELINE_INSERTION")
    warning(
        "SRT imported in Media Pool. Resolve API 21.0.4 has no supported direct "
        .. "SubtitleItem insertion method; insert the imported SRT using timecode."
    )
end

local function write_report_if_possible()
    local text = json_encode(report)
    print("AUTOREEL_REPORT_JSON=" .. text)
    if io ~= nil and type(io.open) == "function" then
        local ok, err = pcall(function()
            local handle = assert(io.open(BUILD.report_path, "wb"))
            handle:write(text)
            handle:write("\n")
            handle:close()
        end)
        if ok then
            log("Report written: " .. BUILD.report_path)
        else
            warning("Could not write report file from Resolve Lua: " .. tostring(err))
        end
    else
        log("Lua file I/O unavailable; report is printed above as AUTOREEL_REPORT_JSON")
    end
end

local function finalize_status()
    local essential_failed =
        report.tracks.V1.failed_events > 0 or report.tracks.A1.failed_events > 0

    if essential_failed or report.timeline_created ~= true then
        report.status = "FAILED"
        return
    end

    local any_failed = false
    for _, row in pairs(report.tracks) do
        if row.failed_events > 0 then any_failed = true end
    end

    if any_failed or #report.unsupported_features > 0 or #report.errors > 0 then
        report.status = "PARTIAL"
    else
        report.status = "SUCCESS"
    end
end

log("START")
local resolve_obj = acquire_resolve()
if resolve_obj == nil then
    fail("Resolve object unavailable")
    finalize_status()
    write_report_if_possible()
    return
end

report.resolve.version = safe_call(resolve_obj, "GetVersionString")
report.resolve.product = safe_call(resolve_obj, "GetProductName")
report.resolve.edition = (
    report.resolve.product ~= nil
    and string.find(string.lower(tostring(report.resolve.product)), "studio", 1, true)
) and "studio" or "free"

local pm = safe_call(resolve_obj, "GetProjectManager")
local project = safe_call(pm, "GetCurrentProject")
if project == nil then
    fail("No Resolve project is open")
    finalize_status()
    write_report_if_possible()
    return
end

report.resolve.project_name = safe_call(project, "GetName")
local media_pool = safe_call(project, "GetMediaPool")
if media_pool == nil then
    fail("Media Pool unavailable")
    finalize_status()
    write_report_if_possible()
    return
end

local name = unique_timeline_name(project, BUILD.timeline_name_base)
local timeline, create_err = safe_call(media_pool, "CreateEmptyTimeline", name)
if timeline == nil then
    fail("CreateEmptyTimeline failed: " .. tostring(create_err))
    finalize_status()
    write_report_if_possible()
    return
end
report.timeline_created = true
report.resolve.timeline_name = name

local current_ok = safe_call(project, "SetCurrentTimeline", timeline)
if current_ok ~= true then
    fail("Could not set the new AutoReel timeline as current")
    finalize_status()
    write_report_if_possible()
    return
end

safe_call(timeline, "SetStartTimecode", "00:00:00:00")
safe_call(timeline, "SetSetting", "timelineResolutionWidth", tostring(BUILD.format.width))
safe_call(timeline, "SetSetting", "timelineResolutionHeight", tostring(BUILD.format.height))

local expected_fps = BUILD.expected_fps.numerator / BUILD.expected_fps.denominator
local actual_fps_raw = safe_call(timeline, "GetSetting", "timelineFrameRate")
local actual_fps = tonumber(actual_fps_raw)
if actual_fps == nil or math.abs(actual_fps - expected_fps) > 0.001 then
    local set_ok = safe_call(
        timeline,
        "SetSetting",
        "timelineFrameRate",
        tostring(BUILD.expected_fps.display)
    )
    actual_fps_raw = safe_call(timeline, "GetSetting", "timelineFrameRate")
    actual_fps = tonumber(actual_fps_raw)
    if set_ok ~= true and (actual_fps == nil or math.abs(actual_fps - expected_fps) > 0.001) then
        fail(
            "New timeline FPS is " .. tostring(actual_fps_raw)
            .. " but M11 plan requires " .. tostring(BUILD.expected_fps.display)
        )
        finalize_status()
        write_report_if_possible()
        return
    end
end

report.resolve.fps = actual_fps_raw
report.resolve.width = safe_call(timeline, "GetSetting", "timelineResolutionWidth")
report.resolve.height = safe_call(timeline, "GetSetting", "timelineResolutionHeight")
report.resolve.start_frame = safe_call(timeline, "GetStartFrame")

local tracks_ok, tracks_err = ensure_tracks(timeline)
if not tracks_ok then
    fail(tracks_err)
    finalize_status()
    write_report_if_possible()
    return
end

report.capabilities.CreateEmptyTimeline = true
report.capabilities.AppendToTimeline = safe_method(media_pool, "AppendToTimeline") ~= nil
report.capabilities.ImportMedia = safe_method(media_pool, "ImportMedia") ~= nil
report.capabilities.AddTrack = safe_method(timeline, "AddTrack") ~= nil
report.capabilities.GetItemListInTrack = safe_method(timeline, "GetItemListInTrack") ~= nil

place_track(media_pool, "V1", 1, 1)
place_track(media_pool, "A1", 1, 2)
place_track(media_pool, "V2", 2, 1)
place_track(media_pool, "A2", 2, 2)
place_track(media_pool, "A3", 3, 2)
try_import_srt(media_pool)

finalize_status()
log("STATUS=" .. report.status)
log("Timeline created: " .. tostring(report.resolve.timeline_name))
write_report_if_possible()
log("END")
"""


def render_runtime(build_data: dict) -> str:
    return LUA_RUNTIME.replace("__BUILD_DATA__", to_lua(build_data, 0))
