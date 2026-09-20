"""Typed M1-internal boundary to replace/test an ASR engine independently."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import TranscriptionConfig


@dataclass(frozen=True)
class Word:
    start_seconds: str
    end_seconds: str
    text: str
    probability: float


@dataclass(frozen=True)
class Segment:
    start_seconds: str
    end_seconds: str
    text: str
    no_speech_probability: float
    words: tuple[Word, ...]


@dataclass(frozen=True)
class Recognition:
    language: str
    language_probability: float
    segments: tuple[Segment, ...]
    engine: str
    engine_version: str
    device: str
    compute_type: str
    warnings: tuple[str, ...] = ()


class TranscriptionBackend(Protocol):
    def recognize(self, audio: Path, config: TranscriptionConfig) -> Recognition: ...
