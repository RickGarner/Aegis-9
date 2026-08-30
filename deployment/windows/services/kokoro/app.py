from __future__ import annotations

import asyncio
import os
import re
import threading
import uuid
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, HTTPException
from kokoro_onnx import Kokoro
from pydantic import BaseModel, ConfigDict, Field


MODEL_ROOT = Path(os.getenv("KOKORO_MODEL_ROOT", r"C:\Aegis9\Models\Kokoro"))
CACHE_ROOT = Path(os.getenv("KOKORO_CACHE_ROOT", str(MODEL_ROOT / "cache")))
MODEL_PATH = MODEL_ROOT / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_ROOT / "voices-v1.0.bin"

app = FastAPI(title="A.E.G.I.S.-9 Kokoro Local Speech", version="1.0.0")
_model: Kokoro | None = None
_model_lock = threading.RLock()


class SynthesisRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(min_length=1, max_length=20_000)
    voice_id: str = Field(default="am_fenrir", alias="voiceId")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    output_format: str = Field(default="wav", alias="outputFormat")
    correlation_id: str | None = Field(default=None, alias="correlationId")


def get_model() -> Kokoro:
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            missing = [str(path) for path in (MODEL_PATH, VOICES_PATH) if not path.is_file()]
            if missing:
                raise RuntimeError("Missing Kokoro model files: " + ", ".join(missing))
            _model = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    return _model


def speech_text(text: str) -> str:
    cleaned = re.sub(r"```[A-Za-z0-9_+.-]*", "", text)
    return cleaned.replace("```", "").strip()


def synthesize(request: SynthesisRequest) -> dict[str, object]:
    if request.output_format.lower() != "wav":
        raise ValueError("A.E.G.I.S.-9 Kokoro currently supports WAV output only.")
    text = speech_text(request.text)
    if not text:
        raise ValueError("No speakable text remained after normalization.")
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    correlation = request.correlation_id or uuid.uuid4().hex
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", correlation)[:80] or uuid.uuid4().hex
    output_path = (CACHE_ROOT / f"speech-{safe_id}.wav").resolve()
    with _model_lock:
        samples, sample_rate = get_model().create(
            text,
            voice=request.voice_id,
            speed=request.speed,
            lang="en-us",
        )
    sf.write(str(output_path), samples, sample_rate)
    duration_ms = int(round((len(samples) / sample_rate) * 1000)) if sample_rate else 0
    return {
        "audioPath": str(output_path),
        "durationMs": duration_ms,
        "sampleRate": int(sample_rate),
        "voiceId": request.voice_id,
    }


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "available": MODEL_PATH.is_file() and VOICES_PATH.is_file(),
        "model": str(MODEL_PATH),
        "voices": str(VOICES_PATH),
    }


@app.post("/synthesize")
async def synthesize_endpoint(request: SynthesisRequest) -> dict[str, object]:
    try:
        return await asyncio.to_thread(synthesize, request)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
