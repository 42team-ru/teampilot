import io
import subprocess
import tempfile
import os
from pathlib import Path

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


def merge_audio_chunks(audio_chunks: list[bytes]) -> tuple[bytes, str, str]:
    """Merge meeting chunks into a single MP3 via ffmpeg.

    Returns (data, content_type, extension). If ffmpeg cannot merge/transcode,
    falls back to concatenated source bytes as webm.
    """
    if not audio_chunks:
        return b"", "application/octet-stream", "bin"

    concatenated = b"".join(audio_chunks)
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            concat_list = tmp_path / "chunks.txt"
            lines = []
            for idx, chunk in enumerate(audio_chunks):
                chunk_path = tmp_path / f"chunk-{idx:06d}.input"
                chunk_path.write_bytes(chunk)
                lines.append(f"file '{chunk_path}'")
            concat_list.write_text("\n".join(lines), encoding="utf-8")

            output_path = tmp_path / "recording.mp3"
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-ar", "44100",
                    "-ac", "2",
                    str(output_path),
                ],
                capture_output=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode(errors="replace"))
            return output_path.read_bytes(), "audio/mpeg", "mp3"
    except Exception as e:
        logger.warning(f"Audio chunk merge failed, uploading concatenated source bytes: {e}")
        return concatenated, "audio/webm", "webm"
