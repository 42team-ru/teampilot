import io
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.types import Message
from loguru import logger

from kafka.producer import EventProducer
from kafka.topics import TOPIC_AUDIO_UPLOAD
from models.events import AudioUploadEvent
from services.minio_client import minio_client

router = Router()


@router.message(F.chat.type == "private", F.audio | F.voice | F.document)
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
        file_data = file_bytes.getvalue()

        content_type = getattr(file_obj, "mime_type", None) or "audio/ogg"
        uploaded = await minio_client.upload_file(
            chat_id=message.chat.id,
            data=file_data,
            filename=file_name,
            content_type=content_type,
        )
        minio_key = uploaded.key

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
