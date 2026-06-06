import io
import subprocess
import tempfile
import os

from loguru import logger


def to_whisper_wav(audio_bytes: bytes) -> bytes:
    """Convert audio to 16kHz mono 16-bit PCM WAV via ffmpeg subprocess.
    Falls back to original bytes if ffmpeg is unavailable."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path + ".wav"
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", tmp_in_path,
                    "-ar", "16000",
                    "-ac", "1",
                    "-sample_fmt", "s16",
                    "-f", "wav",
                    tmp_out_path,
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode(errors="replace"))
            with open(tmp_out_path, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.unlink(tmp_out_path)
    except Exception as e:
        logger.warning(f"Audio conversion failed, using original bytes: {e}")
        return audio_bytes
