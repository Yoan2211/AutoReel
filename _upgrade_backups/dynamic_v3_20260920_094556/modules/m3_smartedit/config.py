from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SmartEditConfig:
    semantic_similarity_threshold: float = 0.72
    topic_similarity_threshold: float = 0.18
    max_section_sentences: int = 4
    weak_formulation_margin: float = 0.15
    auto_remove_exact_duplicates: bool = False

    def __post_init__(self) -> None:
        for name in ("semantic_similarity_threshold", "topic_similarity_threshold",
                     "weak_formulation_margin"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.semantic_similarity_threshold <= self.topic_similarity_threshold:
            raise ValueError("semantic threshold must exceed topic threshold")
        if type(self.max_section_sentences) is not int or self.max_section_sentences < 1:
            raise ValueError("max_section_sentences must be positive")
        if type(self.auto_remove_exact_duplicates) is not bool:
            raise ValueError("auto_remove_exact_duplicates must be boolean")

    def to_contract(self) -> dict:
        return asdict(self)
