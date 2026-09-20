from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    path: Path
    asset_type: str
    tags: tuple[str, ...]
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ValidatedAsset:
    path: Path
    asset_type: str
    sha256: str
    size_bytes: int
    metadata: dict
