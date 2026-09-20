from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MusicPlannerConfig:
    minimum_music_duration_us: int = 8_000_000
    proposal_duration_us: int = 15_000_000
    speech_gain_db: float = -28.0
    no_speech_gain_db: float = -21.0
    fade_in_us: int = 900_000
    fade_out_us: int = 1_200_000
    speech_merge_gap_us: int = 300_000
    minimum_lift_duration_us: int = 1_500_000
    sfx_protection_us: int = 600_000

    def __post_init__(self):
        for name in ("minimum_music_duration_us", "proposal_duration_us", "fade_in_us", "fade_out_us",
                     "speech_merge_gap_us", "minimum_lift_duration_us", "sfx_protection_us"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.minimum_music_duration_us > self.proposal_duration_us:
            raise ValueError("minimum music duration must not exceed proposal duration")
        for name in ("speech_gain_db", "no_speech_gain_db"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not -60 <= value <= 0:
                raise ValueError(f"{name} must be between -60 and 0 dB")
        if not -30 <= self.speech_gain_db <= -25:
            raise ValueError("speech_gain_db must preserve the -30 to -25 dB voice-priority range")
        if self.no_speech_gain_db < self.speech_gain_db:
            raise ValueError("no-speech gain must not be quieter than speech gain")

    def to_contract(self):
        return asdict(self)
