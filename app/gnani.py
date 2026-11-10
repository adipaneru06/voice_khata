"""Gnani AI integration — STT (Prisma) and TTS (Timbre).

All Gnani API calls live in this file and nowhere else.

Docs & Specs from docs.gnani.ai:
--------------------------------
Base URL: https://api.vachana.ai
Authentication: Header "X-API-Key-ID: <GNANI_API_KEY>"

Prisma STT:
  Endpoint: POST https://api.vachana.ai/stt/v3
  Content-Type: multipart/form-data
  Fields:
    - audio_file: WAV audio binary
    - model: "prisma-v3.0"
    - language_code: "indic-auto"
  Response: JSON {"success": true, "transcript": "...", ...}

Timbre TTS:
  Endpoint: POST https://api.vachana.ai/api/v1/tts/inference
  Content-Type: application/json
  Body:
    - text: str
    - model: "timbre-v3.0" (or "timbre-v2.5")
    - voice: "Shivani" (or "Nalini")
    - language: "hi-IN"
    - speed: 1.0
    - audio_config: {"encoding": "linear_pcm", "container": "wav", "num_channels": 1, "sample_rate": 16000, "sample_width": 2}
  Response: Raw binary WAV audio

When MOCK_GNANI=1 is set, this module returns fixed sample data with NO network calls.
"""

import io
import struct
import wave
from typing import Optional, Tuple, Union

import httpx

from app.config import GNANI_API_KEY, MOCK_GNANI

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

GNANI_BASE_URL = "https://api.vachana.ai"
STT_ENDPOINT = f"{GNANI_BASE_URL}/stt/v3"
TTS_ENDPOINT = f"{GNANI_BASE_URL}/api/v1/tts/inference"

# ---------------------------------------------------------------------------
# Mock sample data (SPEC.md Section 4 & 7)
# ---------------------------------------------------------------------------

_MOCK_TRANSCRIPT = "Sharma ji ko 5 kilo chawal, 600 rupaye, udhaar"


def _generate_valid_mock_wav(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate a short valid audio clip (silent 16 kHz mono WAV) in memory."""
    n_samples = int(sample_rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def speech_to_text(
    wav_bytes: bytes,
    return_raw: bool = False,
) -> Union[str, Tuple[str, str]]:
    """Send WAV audio to Gnani Prisma STT and return the transcript string.

    Args:
        wav_bytes: 16 kHz mono WAV audio bytes.
        return_raw: If True, returns tuple of (transcript, raw_response_text).

    Returns:
        transcript string (or tuple if return_raw=True).

    Raises:
        ValueError: If API key is missing or transcript is empty.
        httpx.TimeoutException: If network request times out.
        RuntimeError: If API returns a non-200 status or error payload.
    """
    if MOCK_GNANI:
        mock_raw = '{"success": true, "mock": true, "transcript": "' + _MOCK_TRANSCRIPT + '"}'
        return (_MOCK_TRANSCRIPT, mock_raw) if return_raw else _MOCK_TRANSCRIPT

    if not GNANI_API_KEY:
        raise ValueError("GNANI_API_KEY environment variable is not set. Please add it to .env")

    headers = {
        "X-API-Key-ID": GNANI_API_KEY,
    }

    files = {
        "audio_file": ("audio.wav", wav_bytes, "audio/wav"),
    }
    data = {
        "model": "prisma-v3.0",
        "language_code": "indic-auto",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                STT_ENDPOINT,
                headers=headers,
                files=files,
                data=data,
            )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Gnani Prisma STT request timed out after 30 seconds.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error connecting to Gnani STT API: {exc}") from exc

    raw_text = response.text

    if response.status_code != 200:
        raise RuntimeError(
            f"Gnani STT API returned non-200 status [{response.status_code}]: {raw_text}"
        )

    try:
        resp_json = response.json()
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON returned by Gnani STT: {raw_text}") from exc

    transcript = resp_json.get("transcript")
    if transcript is None:
        raise RuntimeError(f"Missing 'transcript' field in Gnani STT response: {raw_text}")

    transcript = transcript.strip()
    if not transcript:
        raise ValueError("Gnani STT returned an empty transcript. Speech could not be recognized.")

    if return_raw:
        return transcript, raw_text
    return transcript


async def text_to_speech(text: str) -> bytes:
    """Send text to Gnani Timbre TTS and return audio bytes (WAV format).

    Args:
        text: Input text string to synthesize.

    Returns:
        Audio bytes (WAV format).

    Raises:
        ValueError: If text is empty or API key is missing.
        httpx.TimeoutException: If network request times out.
        RuntimeError: If API returns non-200 status or empty audio.
    """
    if MOCK_GNANI:
        return _generate_valid_mock_wav()

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Cannot synthesize speech for empty text.")

    if not GNANI_API_KEY:
        raise ValueError("GNANI_API_KEY environment variable is not set. Please add it to .env")

    headers = {
        "X-API-Key-ID": GNANI_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": cleaned_text,
        "model": "timbre-v3.0",
        "voice": "Shivani",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {
            "encoding": "linear_pcm",
            "container": "wav",
            "num_channels": 1,
            "sample_rate": 16000,
            "sample_width": 2,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TTS_ENDPOINT,
                headers=headers,
                json=payload,
            )

            # Fallback to timbre-v2.5 if timbre-v3.0 voice is not available
            if response.status_code != 200:
                payload["model"] = "timbre-v2.5"
                payload["voice"] = "Nalini"
                response = await client.post(
                    TTS_ENDPOINT,
                    headers=headers,
                    json=payload,
                )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Gnani Timbre TTS request timed out after 30 seconds.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error connecting to Gnani TTS API: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Gnani TTS API returned non-200 status [{response.status_code}]: {response.text}"
        )

    audio_bytes = response.content
    if not audio_bytes:
        raise RuntimeError("Gnani TTS API returned an empty audio response.")

    return audio_bytes
