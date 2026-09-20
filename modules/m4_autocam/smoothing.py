from .framing import CameraState


class CameraSmoother:
    def __init__(self, alpha): self.alpha, self.state = alpha, None
    def reset(self): self.state = None
    def update(self, raw):
        if self.state is None: self.state = raw; return raw
        a, old = self.alpha, self.state
        self.state = CameraState(old.center_x+a*(raw.center_x-old.center_x),
                                 old.center_y+a*(raw.center_y-old.center_y),
                                 old.crop_width+a*(raw.crop_width-old.crop_width),
                                 old.crop_height+a*(raw.crop_height-old.crop_height),
                                 old.zoom+a*(raw.zoom-old.zoom), raw.warning)
        return self.state


def should_keyframe(previous, current, previous_us, current_us, config):
    if previous is None: return True
    center_delta = max(abs(current.center_x-previous.center_x), abs(current.center_y-previous.center_y))
    return (center_delta >= config.center_change_threshold or
            abs(current.zoom-previous.zoom) >= config.zoom_change_threshold or
            current_us-previous_us >= config.keyframe_interval_us or
            current.warning != previous.warning)
