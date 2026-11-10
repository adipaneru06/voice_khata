"""Utility script to test Gnani AI Speech-to-Text and Text-to-Speech directly.

Usage:
  # Speech to text (prints raw response and final transcript):
  python scripts/try_gnani.py stt path/to/audio.wav
  # or simply:
  python scripts/try_gnani.py path/to/audio.wav

  # Text to speech (synthesizes text and saves to out.wav):
  python scripts/try_gnani.py tts "Sharma ji ke khate mein 600 rupaye jod diye"
"""

import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.gnani import speech_to_text, text_to_speech


async def run_stt(wav_path: str):
    if not os.path.exists(wav_path):
        print(f"Error: WAV file not found at '{wav_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Reading audio file: {wav_path} ...")
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    print(f"Sending {len(wav_bytes)} bytes to Gnani Prisma STT...")
    try:
        transcript, raw_response = await speech_to_text(wav_bytes, return_raw=True)
        print("\n" + "=" * 50)
        print("RAW RESPONSE FROM GNANI STT:")
        print("=" * 50)
        print(raw_response)
        print("\n" + "=" * 50)
        print("FINAL TRANSCRIPT:")
        print("=" * 50)
        print(transcript)
        print("=" * 50)
    except Exception as exc:
        print(f"\nSTT Error: {exc}", file=sys.stderr)
        sys.exit(1)


async def run_tts(text: str, output_path: str = "out.wav"):
    print(f"Synthesizing speech for: \"{text}\" ...")
    try:
        audio_bytes = await text_to_speech(text)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"Success! Saved {len(audio_bytes)} bytes to '{output_path}'.")
    except Exception as exc:
        print(f"\nTTS Error: {exc}", file=sys.stderr)
        sys.exit(1)


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    arg1 = sys.argv[1].lower()

    if arg1 == "tts":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Sharma ji ke khate mein 600 rupaye jod diye"
        asyncio.run(run_tts(text))
    elif arg1 == "stt":
        if len(sys.argv) < 3:
            print("Error: Missing WAV file path.\nUsage: python scripts/try_gnani.py stt <path_to_wav>")
            sys.exit(1)
        wav_path = sys.argv[2]
        asyncio.run(run_stt(wav_path))
    elif arg1 in ("-h", "--help"):
        print_help()
    else:
        # Treat single argument as a wav path for STT
        asyncio.run(run_stt(sys.argv[1]))


if __name__ == "__main__":
    main()

