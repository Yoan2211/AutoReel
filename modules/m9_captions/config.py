from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CaptionsConfig:
    minimum_words: int = 2
    target_words: int = 4
    maximum_words: int = 6
    pause_break_us: int = 450_000
    maximum_lines: int = 2
    maximum_characters_per_line: int = 24

    def __post_init__(self):
        if not 1 <= self.minimum_words <= self.target_words <= self.maximum_words:
            raise ValueError("Caption word limits must be ordered positive integers")
        if self.maximum_words > 6 or self.maximum_lines != 2:
            raise ValueError("M9 v1 supports at most six words and exactly two layout lines")
        if type(self.pause_break_us) is not int or self.pause_break_us <= 0:
            raise ValueError("pause_break_us must be a positive integer")
        if type(self.maximum_characters_per_line) is not int or self.maximum_characters_per_line < 8:
            raise ValueError("maximum_characters_per_line is too small")

    def to_contract(self):
        return asdict(self)
