from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AutoCamConfig:
    sample_interval_us: int = 250_000
    output_width: int = 1080
    output_height: int = 1920
    device: str = "auto"
    cpu_fallback: bool = True
    smoothing_alpha: float = 0.22
    lost_hold_us: int = 1_000_000
    keyframe_interval_us: int = 2_000_000
    center_change_threshold: float = 0.025
    zoom_change_threshold: float = 0.012
    natural_zoom_max: float = 1.08
    hard_zoom_max: float = 1.15
    headroom_ratio: float = 0.12

    def __post_init__(self):
        for name in ("sample_interval_us", "output_width", "output_height", "lost_hold_us", "keyframe_interval_us"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("smoothing_alpha", "center_change_threshold", "zoom_change_threshold", "headroom_ratio"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.device not in ("auto", "cpu", "cuda"):
            raise ValueError("device must be auto, cpu or cuda")
        if type(self.cpu_fallback) is not bool:
            raise ValueError("cpu_fallback must be boolean")
        if not 1 <= self.natural_zoom_max <= self.hard_zoom_max <= 1.15:
            raise ValueError("zoom bounds must satisfy 1 <= natural <= hard <= 1.15")

    def to_contract(self):
        return asdict(self)
