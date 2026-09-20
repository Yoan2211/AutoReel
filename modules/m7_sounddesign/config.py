from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SoundDesignConfig:
    minimum_gap_us: int = 3_000_000
    conflict_window_us: int = 300_000
    density_window_us: int = 60_000_000
    maximum_sfx_per_window: int = 8
    zoom_delta_threshold: float = 0.025
    strong_passage_threshold: float = 0.9
    proposal_threshold: float = 0.78
    review_threshold: float = 0.62

    def __post_init__(self):
        for name in ("minimum_gap_us", "conflict_window_us", "density_window_us", "maximum_sfx_per_window"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("zoom_delta_threshold", "strong_passage_threshold", "proposal_threshold", "review_threshold"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.review_threshold > self.proposal_threshold:
            raise ValueError("review threshold must not exceed proposal threshold")

    def to_contract(self):
        return asdict(self)
