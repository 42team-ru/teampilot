import io
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.types import Message
from loguru import logger

from kafka.producer import EventProducer
from kafka.topics import TOPIC_AUDIO_UPLOAD
from models.events import AudioUploadEvent

router = Router()


@router.message(F.audio | F.voice | F.document)
async def handle_audio(message: Message, bot: Bot, producer: EventProducer) -> None:
    await message.answer("⏳ Запись получена, обрабатываю...")

    file_obj = message.audio or message.voice or message.document
    file_id = file_obj.file_id
    duration = getattr(file_obj, "duration", None)
    file_name = getattr(file_obj, "file_name", None) or f"{file_id}.ogg"

    try:
        file_info = await bot.get_file(file_id)
        file_bytes = io.BytesIO()
        await bot.download_file(file_info.file_path, file_bytes)
        file_bytes.seek(0)

        # TODO: upload file_bytes to MinIO
        #   from minio import Minio
        #   from config import settings
        #   client = Minio(settings.MINIO_ENDPOINT,
        #                  access_key=settings.MINIO_ACCESS_KEY,
        #                  secret_key=settings.MINIO_SECRET_KEY,
        #                  secure=False)
        #   minio_key = f"audio/{message.chat.id}/{file_name}"
        #   client.put_object(settings.MINIO_BUCKET_AUDIO, minio_key,
        #                     file_bytes, length=file_bytes.getbuffer().nbytes)
        minio_key = f"audio/{message.chat.id}/{file_name}"  # placeholder until MinIO upload is implemented
        logger.warning(f"MinIO upload not implemented — placeholder key: {minio_key}")

        event = AudioUploadEvent(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            minio_key=minio_key,
            file_name=file_name,
            duration=duration,
            timestamp=datetime.now(timezone.utc),
        )
        await producer.publish(TOPIC_AUDIO_UPLOAD, event)

    except Exception as e:
        logger.error(f"Failed to process audio file {file_id}: {e}")
