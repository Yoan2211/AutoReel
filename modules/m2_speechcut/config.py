"""Conservative, versioned SpeechCut policy."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SpeechCutConfig:
    long_silence_us: int = 1_200_000
    review_pause_us: int = 850_000
    retained_pause_us: int = 420_000
    filler_padding_us: int = 35_000
    filler_max_duration_us: int = 900_000
    repetition_max_gap_us: int = 450_000
    phrase_restart_max_gap_us: int = 900_000
    phrase_restart_min_words: int = 2
    phrase_restart_max_words: int = 6
    false_start_max_words: int = 4
    auto_apply_fillers: bool = True
    auto_apply_repetitions: bool = True

    def __post_init__(self) -> None:
        integer_fields = (
            "long_silence_us", "review_pause_us", "retained_pause_us", "filler_padding_us",
            "filler_max_duration_us", "repetition_max_gap_us",
            "phrase_restart_max_gap_us", "phrase_restart_min_words",
            "phrase_restart_max_words", "false_start_max_words",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.long_silence_us <= self.retained_pause_us:
            raise ValueError("long_silence_us must exceed retained_pause_us")
        if not self.retained_pause_us < self.review_pause_us < self.long_silence_us:
            raise ValueError("review_pause_us must lie between retained and long silence thresholds")
        if self.phrase_restart_min_words < 2:
            raise ValueError("phrase_restart_min_words must be at least 2")
        if self.phrase_restart_max_words < self.phrase_restart_min_words:
            raise ValueError("phrase restart word bounds are reversed")
        if self.false_start_max_words < 1:
            raise ValueError("false_start_max_words must be positive")
        if type(self.auto_apply_fillers) is not bool or type(self.auto_apply_repetitions) is not bool:
            raise ValueError("automatic decision options must be booleans")

    def to_contract(self) -> dict:
        return asdict(self)
