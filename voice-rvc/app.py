"""voice-rvc — локальный OpenAI-совместимый TTS с мем-голосами (RVC voice conversion).

Drop-in замена облачного TTS для llm-worker. Пайплайн в два шага:
    text → edge-tts (нейтральный русский голос) → RVC voice conversion (тембр персонажа).

llm-worker (infra/tts.py) шлёт через OpenAI SDK:
    POST {TTS_API_BASE}/audio/speech  JSON {"model","voice","input","response_format"}
Чтобы переключиться на этот сервис, в llm-worker/.env:
    TTS_API_BASE=http://voice-rvc:5050/v1
    TTS_MODEL=<имя папки в rvc_models>

Заголовок Authorization игнорируется — аутентификация не требуется.

Graceful degradation: если RVC-модель не найдена или конвертация упала, сервис
возвращает базовый edge-tts голос (с warning в логах), а не 500.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path

import edge_tts
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [voice-rvc] %(message)s",
)
log = logging.getLogger("voice-rvc")

# ── Конфигурация из окружения ───────────────────────────────────────────────
MODELS_DIR = Path(os.getenv("RVC_MODELS_DIR", "/app/rvc_models"))
RVC_DEVICE = os.getenv("RVC_DEVICE", "cpu:0")
BASE_TTS_VOICE = os.getenv("BASE_TTS_VOICE", "ru-RU-DmitryNeural")
RVC_F0METHOD = os.getenv("RVC_F0METHOD", "rmvpe")
RVC_INDEX_RATE = float(os.getenv("RVC_INDEX_RATE", "0.75"))
RVC_PROTECT = float(os.getenv("RVC_PROTECT", "0.33"))
RVC_F0UP_KEY = int(os.getenv("RVC_F0UP_KEY", "0"))
PORT = int(os.getenv("PORT", "5050"))

# normalize device: rvc-python ждёт вид "cpu:0" / "cuda:0"
if RVC_DEVICE == "cpu":
    RVC_DEVICE = "cpu:0"

app = FastAPI(title="voice-rvc TTS", docs_url=None, redoc_url=None)


# ── Ленивая загрузка / кэш RVC-моделей ──────────────────────────────────────
class _RvcEngine:
    """Обёртка над rvc_python.RVCInference с ленивой инициализацией и кэшем
    загруженной модели. Потокобезопасна (один глобальный lock — инференс RVC
    держит модель в памяти и не реентерабелен)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inference = None  # RVCInference, создаётся при первом использовании
        self._loaded_model: str | None = None
        self._import_error: str | None = None

    def _ensure_inference(self) -> bool:
        if self._inference is not None:
            return True
        if self._import_error is not None:
            return False
        try:
            import torch
            # PyTorch 2.6 сменил дефолт weights_only на True → fairseq/RVC чекпоинты
            # (содержат глобал fairseq.data.dictionary.Dictionary) перестают грузиться.
            # Файлы локальные и доверенные — возвращаем прежнее поведение torch.load.
            if not getattr(torch.load, "_voicervc_patched", False):
                _orig_load = torch.load

                def _patched_load(*args, **kwargs):
                    kwargs.setdefault("weights_only", False)
                    return _orig_load(*args, **kwargs)

                _patched_load._voicervc_patched = True
                torch.load = _patched_load

            from rvc_python.infer import RVCInference  # тяжёлый импорт (torch)
        except Exception as e:  # noqa: BLE001
            self._import_error = str(e)
            log.warning("rvc-python недоступен (%s) — RVC отключён, отдаю базовый голос", e)
            return False
        try:
            self._inference = RVCInference(
                models_dir=str(MODELS_DIR),
                device=RVC_DEVICE,
            )
            self._inference.set_params(
                f0method=RVC_F0METHOD,
                f0up_key=RVC_F0UP_KEY,
                index_rate=RVC_INDEX_RATE,
                protect=RVC_PROTECT,
            )
        except Exception as e:  # noqa: BLE001
            self._import_error = str(e)
            log.warning("Не удалось инициализировать RVCInference (%s) — отдаю базовый голос", e)
            return False
        return True

    def list_models(self) -> list[str]:
        if not MODELS_DIR.is_dir():
            return []
        names: list[str] = []
        for child in sorted(MODELS_DIR.iterdir()):
            if child.is_dir() and any(child.glob("*.pth")):
                names.append(child.name)
        return names

    def _detect_version(self, model: str) -> str:
        """Определяет версию RVC-модели (v1/v2) по чекпоинту: форма emb_phone
        256 → v1, 768 → v2. rvc-python по умолчанию грузит v2, и на v1-модели
        падает size mismatch — поэтому детектим явно."""
        try:
            import torch
            pth = next((MODELS_DIR / model).glob("*.pth"))
            cpt = torch.load(str(pth), map_location="cpu", weights_only=False)
            v = cpt.get("version") if isinstance(cpt, dict) else None
            if v in ("v1", "v2"):
                return v
            dim = cpt["weight"]["enc_p.emb_phone.weight"].shape[1]
            return "v1" if dim == 256 else "v2"
        except Exception as e:  # noqa: BLE001
            log.warning("Не смог определить версию модели %r (%s) — пробую v2", model, e)
            return "v2"

    def convert(self, model: str, in_wav: str, out_wav: str) -> bool:
        """Конвертирует in_wav голосом model в out_wav. True — успех, False —
        деградация (вызывающий отдаёт исходный базовый голос)."""
        if model not in self.list_models():
            log.warning("RVC-модель %r не найдена в %s — базовый голос", model, MODELS_DIR)
            return False
        with self._lock:
            if not self._ensure_inference():
                return False
            try:
                if self._loaded_model != model:
                    version = self._detect_version(model)
                    self._inference.load_model(model, version=version)
                    self._loaded_model = model
                    log.info("RVC-модель загружена: %s (version=%s)", model, version)
                self._inference.infer_file(in_wav, out_wav)
                return True
            except Exception as e:  # noqa: BLE001
                log.warning("RVC convert упал для модели %r (%s) — базовый голос", model, e)
                # сбросим кэш, чтобы следующий запрос попытался переинициализировать
                self._loaded_model = None
                return False


_engine = _RvcEngine()


# ── Аудио-помощники ─────────────────────────────────────────────────────────
async def _edge_tts_to_mp3(text: str, voice: str, out_mp3: str) -> None:
    """Базовый нейтральный голос через edge-tts → mp3 на диск."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_mp3)


def _ffmpeg(args: list[str]) -> None:
    """Запускает ffmpeg, кидает с понятным сообщением при ошибке."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")


def _to_wav(src: str, dst_wav: str) -> None:
    # RVC лучше работает с 16k mono; rvc-python ресемплит сам, но дадим чистый wav
    _ffmpeg(["-i", src, "-ar", "16000", "-ac", "1", "-f", "wav", dst_wav])


def _encode(src_wav: str, response_format: str) -> tuple[bytes, str]:
    """Кодирует wav в нужный формат. Возвращает (bytes, media_type)."""
    fmt = (response_format or "mp3").lower()
    if fmt == "wav":
        with open(src_wav, "rb") as f:
            return f.read(), "audio/wav"
    # дефолт — mp3
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        out = tmp.name
    try:
        _ffmpeg(["-i", src_wav, "-f", "mp3", out])
        with open(out, "rb") as f:
            return f.read(), "audio/mpeg"
    finally:
        _safe_unlink(out)


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# ── OpenAI-совместимый API ──────────────────────────────────────────────────
class SpeechRequest(BaseModel):
    model: str = ""           # имя RVC-модели = имя папки в rvc_models
    input: str                # текст для синтеза
    voice: str = ""           # опц. базовый edge-tts голос; пусто → BASE_TTS_VOICE
    response_format: str = "mp3"


@app.post("/v1/audio/speech")
async def audio_speech(req: SpeechRequest) -> Response:
    text = (req.input or "").strip()
    if not text:
        return JSONResponse(status_code=400, content={"error": "input is required"})

    base_voice = req.voice.strip() or BASE_TTS_VOICE

    workdir = tempfile.mkdtemp(prefix="voice-rvc-")
    base_mp3 = os.path.join(workdir, "base.mp3")
    base_wav = os.path.join(workdir, "base.wav")
    rvc_wav = os.path.join(workdir, "rvc.wav")
    try:
        # 1) Базовый нейтральный голос
        await _edge_tts_to_mp3(text, base_voice, base_mp3)
        await asyncio.to_thread(_to_wav, base_mp3, base_wav)

        # 2) RVC voice conversion (в threadpool — блокирующий torch)
        final_wav = base_wav
        if req.model:
            ok = await asyncio.to_thread(_engine.convert, req.model, base_wav, rvc_wav)
            if ok:
                final_wav = rvc_wav

        # 3) Кодирование в нужный формат
        audio, media_type = await asyncio.to_thread(_encode, final_wav, req.response_format)
        return Response(content=audio, media_type=media_type)
    except Exception as e:  # noqa: BLE001
        log.exception("speech synthesis failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        for p in (base_mp3, base_wav, rvc_wav):
            _safe_unlink(p)
        try:
            os.rmdir(workdir)
        except OSError:
            pass


@app.get("/v1/models")
async def list_models() -> JSONResponse:
    names = _engine.list_models()
    return JSONResponse(
        content={
            "object": "list",
            "data": [{"id": n, "object": "model", "owned_by": "voice-rvc"} for n in names],
        }
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
