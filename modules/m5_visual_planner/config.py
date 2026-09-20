from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VisualPlannerConfig:
    minimum_gap_us: int = 3_500_000
    maximum_visuals_per_section: int = 2
    target_duration_us: int = 2_500_000
    minimum_duration_us: int = 900_000
    maximum_duration_us: int = 4_500_000
    auto_confidence_threshold: float = 0.78

    def __post_init__(self):
        for name in ("minimum_gap_us", "maximum_visuals_per_section", "target_duration_us",
                     "minimum_duration_us", "maximum_duration_us"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not self.minimum_duration_us <= self.target_duration_us <= self.maximum_duration_us:
            raise ValueError("duration bounds must satisfy minimum <= target <= maximum")
        if isinstance(self.auto_confidence_threshold, bool) or not isinstance(self.auto_confidence_threshold, (int, float)) or not 0 <= self.auto_confidence_threshold <= 1:
            raise ValueError("auto_confidence_threshold must be between 0 and 1")

    def to_contract(self):
        return asdict(self)
