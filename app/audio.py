"""Audio conversion: webm/opus/ogg/any -> 16 kHz mono WAV using ffmpeg."""

import os
import shutil
import subprocess
import tempfile


def get_ffmpeg_binary() -> str | None:
    """Find ffmpeg binary in system PATH, project directory, or via imageio_ffmpeg."""
    # 1. Check project directory
    local_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ffmpeg.exe"))
    if os.path.isfile(local_bin):
        return local_bin

    # 2. Check system PATH
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd

    # 3. Check imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except (ImportError, Exception):
        pass

    # 4. Check common Windows paths
    common_paths = [
        os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"),
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p

    return None


def convert_to_wav(input_bytes: bytes, filename: str = "recording.webm") -> bytes:
    """Convert input audio bytes (e.g. webm, ogg, mp4, wav) to 16 kHz mono WAV using ffmpeg.

    Raises:
        RuntimeError: If ffmpeg is not installed or conversion fails.
    """
    if not input_bytes:
        raise RuntimeError("Audio file is empty.")

    ffmpeg_bin = get_ffmpeg_binary()
    if not ffmpeg_bin:
        raise RuntimeError(
            "ffmpeg is not installed or not found in system PATH. "
            "Please install ffmpeg to enable audio conversion."
        )

    # Preserve file extension so ffmpeg selects the correct demuxer
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    if not ext or ext not in [".webm", ".mp4", ".ogg", ".wav", ".m4a", ".aac"]:
        ext = ".webm"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, f"input_audio{ext}")
        output_file = os.path.join(tmpdir, "output.wav")

        with open(input_file, "wb") as f:
            f.write(input_bytes)

        cmd = [
            ffmpeg_bin, "-y",
            "-i", input_file,
            "-ar", "16000",
            "-ac", "1",
            "-sample_fmt", "s16",
            output_file,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "ffmpeg is not installed or not found in system PATH. "
                "Please install ffmpeg to enable audio conversion."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Audio conversion with ffmpeg timed out after 30 seconds.") from exc

        if proc.returncode != 0:
            error_msg = proc.stderr.decode(errors="replace")
            # Return a clean, user-friendly error instead of dumping the compiler/library headers
            if "invalid data found" in error_msg.lower() or "end of file" in error_msg.lower():
                raise RuntimeError("Audio recording was too short or incomplete. Please hold the mic, speak clearly, and try again.")
            last_line = error_msg.strip().splitlines()[-1] if error_msg.strip() else "Unknown conversion error"
            raise RuntimeError(f"Audio conversion failed: {last_line}")

        with open(output_file, "rb") as f:
            return f.read()
