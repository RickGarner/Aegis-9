from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

from app.config import Settings


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    confidence: float
    runtime: str


class LocalWhisperService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: WhisperModel | None = None
        self._runtime = "unloaded"
        self._lock = Lock()

    def transcribe(self, audio_path: Path) -> Transcription:
        with self._lock:
            model = self._get_model()
            segments, info = model.transcribe(
                str(audio_path),
                language="en",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt="A.E.G.I.S.-9 local assistant. LM Studio, Ollama, LiteLLM, MOVEit Automation, Aegis Developer Studio, FERAL.",
            )
            collected = list(segments)
        text = " ".join(segment.text.strip() for segment in collected if segment.text.strip()).strip()
        log_probabilities = [segment.avg_logprob for segment in collected]
        confidence = math.exp(sum(log_probabilities) / len(log_probabilities)) if log_probabilities else 0.0
        return Transcription(
            text=text,
            language=info.language or "en",
            confidence=max(0.0, min(1.0, confidence)),
            runtime=self._runtime,
        )

    def _get_model(self) -> WhisperModel:
        if self._model is not None:
            return self._model
        requested_device = self._settings.whisper_device.lower()
        requested_compute = self._settings.whisper_compute_type.lower()
        if requested_device == "auto":
            try:
                self._model = WhisperModel(
                    self._settings.whisper_model,
                    device="cuda",
                    compute_type="float16" if requested_compute == "auto" else requested_compute,
                )
                self._runtime = "cuda"
                return self._model
            except (RuntimeError, ValueError):
                pass
        device = "cpu" if requested_device == "auto" else requested_device
        compute_type = "int8" if requested_compute == "auto" and device == "cpu" else requested_compute
        self._model = WhisperModel(self._settings.whisper_model, device=device, compute_type=compute_type)
        self._runtime = device
        return self._model
