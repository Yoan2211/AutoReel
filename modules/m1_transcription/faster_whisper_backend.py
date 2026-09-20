"""Optional local faster-whisper adapter. No cloud transcription calls."""

from importlib.metadata import version
from pathlib import Path

from .audio import is_digital_silence
from .backend import Recognition, Segment, Word
from .config import TranscriptionConfig
from .errors import TranscriptionError


class FasterWhisperBackend:
    def recognize(self, audio: Path, config: TranscriptionConfig) -> Recognition:
        if is_digital_silence(audio):
            return Recognition(config.language or "und", 0.0, (), "pcm-silence-check",
                               "1.0.0", "cpu", "pcm_s16le")
        try:
            import ctranslate2
            from faster_whisper import WhisperModel
            from faster_whisper.utils import download_model
        except ImportError as exc:
            raise TranscriptionError('Install the ASR engine: pip install -e ".[transcription]"') from exc

        try:
            model_path = Path(config.model)
            if not model_path.is_dir():
                model_path = Path(download_model(
                    config.model, cache_dir=config.models_dir,
                    local_files_only=not config.allow_model_download,
                ))
            # Prevent faster-whisper's implicit tokenizer download for incomplete local models.
            for name in ("model.bin", "config.json", "tokenizer.json"):
                if not (model_path / name).is_file():
                    raise TranscriptionError(f"Incomplete local model: missing {name}")
        except Exception as exc:
            # Model resolution is a third-party boundary (filesystem, cache, HTTP).
            raise TranscriptionError(
                f"Model unavailable: {config.model}. Supply a local model or explicitly "
                f"enable allow_model_download. Details: {exc}"
            ) from exc

        requested = config.device
        device_warnings = ()
        if requested == "auto":
            try:
                requested = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except RuntimeError as exc:
                if not config.cpu_fallback:
                    raise TranscriptionError(f"GPU discovery failed: {exc}") from exc
                requested, device_warnings = "cpu", ("CPU_FALLBACK",)

        def run(device: str, warnings: tuple[str, ...] = ()) -> Recognition:
            compute = "int8" if device == "cpu" else "float16"
            model = WhisperModel(str(model_path), device=device, compute_type=compute,
                                 cpu_threads=config.cpu_threads, local_files_only=True)
            segments, info = model.transcribe(
                str(audio), language=config.language, task="transcribe",
                beam_size=config.beam_size, word_timestamps=True, vad_filter=False,
                condition_on_previous_text=False, temperature=0.0,
            )
            # Consume the lazy generator here so GPU runtime failures can trigger fallback.
            recognized = tuple(
                Segment(str(s.start), str(s.end), s.text, float(s.no_speech_prob),
                        tuple(Word(str(w.start), str(w.end), w.word, float(w.probability))
                              for w in (s.words or ())))
                for s in segments
            )
            return Recognition(info.language, float(info.language_probability), recognized,
                               "faster-whisper", version("faster-whisper"), device, compute, warnings)

        try:
            return run(requested, device_warnings)
        except ValueError as exc:
            raise TranscriptionError(f"Invalid ASR request: {exc}") from exc
        except (RuntimeError, OSError) as exc:
            if requested == "cuda" and config.cpu_fallback:
                try:
                    return run("cpu", ("CPU_FALLBACK",))
                except (RuntimeError, OSError, ValueError) as cpu_exc:
                    raise TranscriptionError(f"CPU fallback failed: {cpu_exc}") from cpu_exc
            raise TranscriptionError(f"ASR execution failed: {exc}") from exc
