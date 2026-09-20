from dataclasses import dataclass


@dataclass(frozen=True)
class CameraState:
    center_x: float
    center_y: float
    crop_width: float
    crop_height: float
    zoom: float
    warning: str | None = None


def calculate(width, height, subjects, config):
    target_aspect = config.output_width / config.output_height
    source_aspect = width / height
    if source_aspect >= target_aspect:
        base_w, base_h = target_aspect / source_aspect, 1.0
    else:
        base_w, base_h = 1.0, source_aspect / target_aspect
    if not subjects:
        return CameraState(.5, .5, base_w, base_h, 1.0, "NO_SUBJECT")
    boxes = [item[1] for item in subjects]
    left, right = min(b.x for b in boxes), max(b.x+b.width for b in boxes)
    top, bottom = min(b.y for b in boxes), max(b.y+b.height for b in boxes)
    warning = "SUBJECTS_EXCEED_VERTICAL_FRAME" if right-left > base_w*.92 or bottom-top > base_h*.92 else None
    zoom = 1.0
    if len(boxes) == 1 and warning is None:
        box = boxes[0]
        desired = .30 / max(.001, box.height / base_h) if box.kind == "face" else .70 / max(.001, box.height / base_h)
        limit = config.hard_zoom_max if box.kind == "face" and box.height < .12 else config.natural_zoom_max
        zoom = max(1.0, min(limit, desired))
    crop_w, crop_h = base_w/zoom, base_h/zoom
    center_x = (left+right)/2
    center_y = (top+bottom)/2 - config.headroom_ratio*crop_h
    center_x = max(crop_w/2, min(1-crop_w/2, center_x))
    center_y = max(crop_h/2, min(1-crop_h/2, center_y))
    return CameraState(center_x, center_y, crop_w, crop_h, zoom, warning)
