from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from kafka.producer import EventProducer
from kafka.topics import Topics
from models.events import FileUploadedEvent
from services.minio_client import minio_client
from states.upload import FileUploadStates

router = Router()

UPLOAD_PROMPT_TEXT = (
    "Отправьте аудио или видео для загрузки. Поддерживаемые типы: аудио, голосовое, видео, видеосообщение.\n"
    "Используйте /cancel для отмены."
)


@dataclass(frozen=True)
class TelegramFilePayload:
    file_id: str
    original_filename: str
    content_type: str
    file_size: int | None


@router.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext) -> None:
    from services.team_service import get_member_teams, get_my_teams
    import asyncio
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(message.from_user.id),
        get_member_teams(message.from_user.id),
    )
    all_teams = [t for t in (manager_teams + member_teams) if t.get("telegramChatId")]

    if not all_teams:
        await message.answer(
            "⚠️ Нет команд с привязанным чатом.\n"
            "Менеджер должен сначала привязать Telegram-чат к команде.\n\n"
            "Используйте кнопку 📤 в контексте нужной команды через меню 🏢 Мои команды."
        )
        return

    if len(all_teams) == 1:
        team = all_teams[0]
        chat_id = int(team["telegramChatId"])
        await state.update_data(upload_team_chat_id=chat_id)
        await state.set_state(FileUploadStates.waiting_for_file)
        team_title = team.get("chatTitle") or str(team.get("id"))
        from html import escape
        await message.answer(
            f"📤 Загрузка файла для команды <b>{escape(team_title)}</b>\n\n"
            + UPLOAD_PROMPT_TEXT
        )
        return

    # Multiple teams — ask user to use the button in team context
    await message.answer(
        "Вы состоите в нескольких командах.\n"
        "Используйте кнопку 📤 Загрузить файл в контексте нужной команды:\n\n"
        "🏢 Мои команды → выберите команду → 📤 Загрузить файл"
    )


@router.message(FileUploadStates.waiting_for_file, Command("cancel"))
async def cmd_cancel_upload(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Загрузка отменена.")


@router.message(
    FileUploadStates.waiting_for_file,
    F.audio | F.voice | F.video | F.video_note,
)
async def handle_upload_file(
    message: Message,
    bot: Bot,
    producer: EventProducer,
    state: FSMContext,
) -> None:
    payload = _extract_file_payload(message)
    if payload is None:
        await message.answer("Пожалуйста, отправьте аудио или видео файл. Используйте /cancel для отмены.")
        return

    if message.from_user is None:
        await message.answer("Не удалось загрузить файл: отсутствуют данные пользователя Telegram.")
        return

    data = await state.get_data()
    team_chat_id: int | None = data.get("upload_team_chat_id")
    if team_chat_id is None:
        await message.answer(
            "⚠️ Не выбрана команда для загрузки.\n"
            "Используйте кнопку 📤 в контексте команды через меню 🏢 Мои команды."
        )
        await state.clear()
        return

    progress_message = await message.answer("Загружаю файл...")
    try:
        file_bytes = await _download_file(bot, payload.file_id)
        uploaded = await minio_client.upload_file(
            chat_id=team_chat_id,
            data=file_bytes,
            filename=payload.original_filename,
            content_type=payload.content_type,
        )

        event = FileUploadedEvent(
            user_id=message.from_user.id,
            chat_id=team_chat_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            minio_bucket=uploaded.bucket,
            minio_key=uploaded.key,
            file_size=payload.file_size or len(file_bytes),
            uploaded_at=datetime.now(timezone.utc),
        )
        await producer.publish(Topics.FILES_UPLOADED, event, key=uploaded.key)
    except Exception as e:
        logger.exception(f"Failed to upload Telegram file: {e}")
        await progress_message.edit_text("Ошибка загрузки файла. Пожалуйста, попробуйте позже.")
        return

    await state.clear()
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])
    await progress_message.edit_text("✅ Файл успешно загружен.", reply_markup=kb)


@router.message(
    FileUploadStates.waiting_for_file,
    F.document | F.photo,
)
async def handle_unsupported_file_type(message: Message) -> None:
    await message.answer(
        "Этот тип файла не поддерживается. Отправьте аудио или видео.\n"
        "Используйте /cancel для отмены."
    )


@router.message(FileUploadStates.waiting_for_file)
async def handle_non_file_while_waiting(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте аудио или видео файл. Используйте /cancel для отмены.")


async def _download_file(bot: Bot, file_id: str) -> bytes:
    file_info = await bot.get_file(file_id)
    if not file_info.file_path:
        raise RuntimeError(f"Telegram file path is missing for file_id={file_id}")

    file_bytes = io.BytesIO()
    await bot.download_file(file_info.file_path, file_bytes)
    return file_bytes.getvalue()


def _extract_file_payload(message: Message) -> TelegramFilePayload | None:
    if message.audio:
        return _payload_from_object(
            message.audio,
            fallback_filename=f"audio_{message.audio.file_unique_id}.mp3",
            default_content_type="audio/mpeg",
        )
    if message.voice:
        return _payload_from_object(
            message.voice,
            fallback_filename=f"voice_{message.voice.file_unique_id}.ogg",
            default_content_type="audio/ogg",
        )
    if message.video:
        return _payload_from_object(
            message.video,
            fallback_filename=f"video_{message.video.file_unique_id}.mp4",
            default_content_type="video/mp4",
        )
    if message.video_note:
        return _payload_from_object(
            message.video_note,
            fallback_filename=f"video_note_{message.video_note.file_unique_id}.mp4",
            default_content_type="video/mp4",
        )
    return None


def _payload_from_object(
    file_object: object,
    *,
    fallback_filename: str,
    default_content_type: str,
) -> TelegramFilePayload:
    raw_filename = getattr(file_object, "file_name", None) or fallback_filename
    return TelegramFilePayload(
        file_id=getattr(file_object, "file_id"),
        original_filename=_safe_filename(raw_filename, fallback_filename),
        content_type=getattr(file_object, "mime_type", None) or default_content_type,
        file_size=getattr(file_object, "file_size", None),
    )


def _safe_filename(filename: str, fallback: str) -> str:
    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return normalized or fallback
