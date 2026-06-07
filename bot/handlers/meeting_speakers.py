from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from services import meeting_speaker_service

router = Router()


@router.callback_query(F.data.startswith("msel:"))
async def meeting_speaker_select(callback: CallbackQuery) -> None:
    meeting_id, speaker_label = _parse_speaker_ref(callback.data)
    if not meeting_id:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    try:
        resp = await meeting_speaker_service.get_speaker_candidates(meeting_id, callback.from_user.id)
    except Exception:
        await callback.answer("Не удалось связаться с backend", show_alert=True)
        return

    if resp.status_code == 403:
        await callback.answer("Только менеджер команды может сопоставлять говорящих", show_alert=True)
        return
    if resp.status_code != 200:
        await callback.answer(f"Backend вернул {resp.status_code}", show_alert=True)
        return

    candidates = resp.json()
    rows: list[list[InlineKeyboardButton]] = []
    for candidate in candidates[:20]:
        telegram_id = candidate.get("telegramId")
        if telegram_id is None:
            continue
        rows.append([InlineKeyboardButton(
            text=_candidate_title(candidate),
            callback_data=f"mss:{meeting_id.replace('-', '')}:{speaker_label.split('_')[-1]}:{telegram_id}",
        )])
    rows.append([InlineKeyboardButton(
        text="Гость / не участник команды",
        callback_data=f"mss:{meeting_id.replace('-', '')}:{speaker_label.split('_')[-1]}:0",
    )])

    await callback.message.answer(
        f"Кто говорил как <b>{escape(speaker_label)}</b>?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mss:"))
async def meeting_speaker_set(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return
    meeting_id = _restore_uuid(parts[1])
    speaker_number = _parse_positive_int(parts[2])
    participant_id = _parse_non_negative_int(parts[3])
    if speaker_number is None or participant_id is None:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return
    speaker_label = f"SPEAKER_{speaker_number}"
    try:
        resp = await meeting_speaker_service.map_speaker(
            meeting_id,
            speaker_label,
            None if participant_id == 0 else participant_id,
            callback.from_user.id,
        )
    except Exception:
        await callback.answer("Не удалось связаться с backend", show_alert=True)
        return

    if resp.status_code == 200:
        data = resp.json()
        await callback.message.edit_text(
            f"✅ <b>{escape(data.get('speakerLabel') or speaker_label)}</b> → {escape(data.get('displayName') or 'Гость')}",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("Сопоставление сохранено")
    elif resp.status_code == 403:
        await callback.answer("Только менеджер команды может сопоставлять говорящих", show_alert=True)
    else:
        await callback.answer(f"Backend вернул {resp.status_code}", show_alert=True)


def _parse_speaker_ref(data: str) -> tuple[str | None, str]:
    parts = data.split(":")
    if len(parts) != 3:
        return None, ""
    speaker_number = _parse_positive_int(parts[2])
    if speaker_number is None:
        return None, ""
    return _restore_uuid(parts[1]), f"SPEAKER_{speaker_number}"


def _restore_uuid(value: str) -> str:
    if len(value) != 32:
        return value
    return f"{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}"


def _candidate_title(candidate: dict) -> str:
    username = candidate.get("username")
    full_name = candidate.get("fullName") or ""
    if username:
        return f"@{username}"
    if full_name:
        return full_name
    return str(candidate.get("telegramId"))


def _parse_positive_int(value: str) -> int | None:
    parsed = _parse_non_negative_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _parse_non_negative_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
