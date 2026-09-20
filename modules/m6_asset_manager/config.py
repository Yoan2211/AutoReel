from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AssetManagerConfig:
    resolved_score_threshold: float = 0.72
    review_score_threshold: float = 0.5
    recursive: bool = True
    ffprobe_path: str = "ffprobe"

    def __post_init__(self):
        for name in ("resolved_score_threshold", "review_score_threshold"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.review_score_threshold > self.resolved_score_threshold:
            raise ValueError("review threshold must not exceed resolved threshold")
        if type(self.recursive) is not bool:
            raise ValueError("recursive must be boolean")
        if not isinstance(self.ffprobe_path, str) or not self.ffprobe_path:
            raise ValueError("ffprobe_path must be non-empty")

    def to_contract(self):
        return asdict(self)
