import asyncio
import json
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from confluent_kafka import Consumer
from loguru import logger

from config import settings
from kafka.topics import (
    TOPIC_BOTS_NOTIFICATIONS,
    TOPIC_BOTS_TASKS,
    TOPIC_TASKS_STATE,
)
from keyboards.sync import (
    build_task_approval_keyboard,
    build_sync_summary_keyboard,
)
from models.events import (
    BotNotificationEvent,
    BotSyncEvent,
    SyncMemberSummary,
    TaskConfirmationEvent,
    TaskStateEvent,
)
from services import sync_state

_SYNC_TYPES = {"SYNC_PROMPT", "SYNC_SUMMARY"}

_DISPLAY_TZ = timezone(timedelta(hours=3))
_BATCH_WINDOW_SECS = 3

# Cache of per-member sync summaries for the drilldown ("📋 Отчёт по участникам") view.
# Keyed by team_id (string). Overwritten on each new summary — ephemeral hackathon data.
# Each entry: {"overview": <overview text>, "members": [SyncMemberSummary, ...]}
_summary_members_cache: dict[str, dict] = {}


class EventConsumer:
    TOPICS = [
        TOPIC_TASKS_STATE,
        TOPIC_BOTS_TASKS,
        TOPIC_BOTS_NOTIFICATIONS,
    ]

    def __init__(self) -> None:
        self._pending_confirmations: dict[int, list[TaskConfirmationEvent]] = {}
        self._confirmation_flush: dict[int, asyncio.Task] = {}
        self._pending_states: dict[int, list[TaskStateEvent]] = {}
        self._state_flush: dict[int, asyncio.Task] = {}

    async def start(self, bot: Bot) -> None:
        consumer = Consumer({
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "tg-bot-consumer",
            "auto.offset.reset": "latest",
        })
        consumer.subscribe(self.TOPICS)
        logger.info(f"Kafka consumer subscribed to: {self.TOPICS}")

        try:
            while True:
                msg = await asyncio.to_thread(consumer.poll, 0.1)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Kafka consumer error: {msg.error()}")
                    continue

                try:
                    await self._dispatch(bot, msg.topic(), msg.value())
                except Exception as e:
                    logger.error(f"Error dispatching message from {msg.topic()}: {e}")
        finally:
            consumer.close()

    async def _dispatch(self, bot: Bot, topic: str, payload: bytes) -> None:
        if payload is None:
            logger.warning("Kafka message from {} has empty payload", topic)
            return

        if topic == TOPIC_TASKS_STATE:
            event = TaskStateEvent.model_validate_json(payload)
            if event.type != "CREATED":
                await self._queue_state(bot, event)

        elif topic == TOPIC_BOTS_NOTIFICATIONS:
            raw = json.loads(payload)
            if raw.get("type") in _SYNC_TYPES:
                event = BotSyncEvent.model_validate(raw)
                await self._handle_sync_notification(bot, event)
            else:
                event = BotNotificationEvent.model_validate(raw)
                await self._send_bot_notification(bot, event)

        elif topic == TOPIC_BOTS_TASKS:
            event = TaskConfirmationEvent.model_validate_json(payload)
            await self._queue_confirmation(bot, event)

    async def _queue_confirmation(self, bot: Bot, event: TaskConfirmationEvent) -> None:
        recipient_ids = _unique_ids(event.recipient_telegram_ids)
        if not recipient_ids:
            logger.warning("TaskConfirmationEvent {} has no DM recipients", event.task_id)
            return

        for recipient_id in recipient_ids:
            self._pending_confirmations.setdefault(recipient_id, []).append(event)
            if recipient_id not in self._confirmation_flush or self._confirmation_flush[recipient_id].done():
                self._confirmation_flush[recipient_id] = asyncio.create_task(
                    self._flush_confirmations(bot, recipient_id)
                )

    async def _flush_confirmations(self, bot: Bot, recipient_id: int) -> None:
        await asyncio.sleep(_BATCH_WINDOW_SECS)
        events = self._pending_confirmations.pop(recipient_id, [])
        if not events:
            return
        if len(events) == 1:
            event = events[0]
            if not event.auto_confirmed and event.task_id:
                kb = build_task_approval_keyboard(event.task_id)
            else:
                kb = None
            await self._send_to_recipients(
                bot,
                recipient_ids=[recipient_id],
                text=self._format_task_confirmation(event),
                parse_mode="HTML",
                reply_markup=kb,
                event_name="TaskConfirmationEvent",
                event_id=event.task_id,
            )
            return

        auto = all(e.auto_confirmed for e in events)
        header = f"🤖 <b>Создано задач автоматически: {len(events)}</b>" if auto else f"<b>Создано задач: {len(events)}</b>"
        lines = [header, ""]
        for i, e in enumerate(events, 1):
            lines.append(f"{i}. <b>{escape(e.title)}</b>")
            if e.column_title:
                lines.append(f"   📂 {escape(e.column_title)}")
            if e.assignee_username:
                lines.append(f"   👤 @{escape(e.assignee_username)}")
            if e.deadline:
                lines.append(f"   ⏰ {_format_deadline(e.deadline)}")
        await self._send_to_recipients(
            bot,
            recipient_ids=[recipient_id],
            text="\n".join(lines),
            parse_mode="HTML",
            event_name="TaskConfirmationBatch",
            event_id=str(len(events)),
        )

    async def _queue_state(self, bot: Bot, event: TaskStateEvent) -> None:
        recipient_ids = _unique_ids(event.recipient_telegram_ids)
        if not recipient_ids:
            logger.warning("TaskStateEvent {} has no DM recipients", event.task_id)
            return

        for recipient_id in recipient_ids:
            self._pending_states.setdefault(recipient_id, []).append(event)
            if recipient_id not in self._state_flush or self._state_flush[recipient_id].done():
                self._state_flush[recipient_id] = asyncio.create_task(
                    self._flush_states(bot, recipient_id)
                )

    async def _flush_states(self, bot: Bot, recipient_id: int) -> None:
        await asyncio.sleep(_BATCH_WINDOW_SECS)
        events = self._pending_states.pop(recipient_id, [])
        if not events:
            return

        cancelled = [e for e in events if e.type == "CANCELLED"]
        moved = [e for e in events if e.type == "COLUMN_CHANGED"]
        updated = [e for e in events if e.type == "UPDATED"]

        if cancelled:
            if len(cancelled) == 1:
                await self._send_task_state(bot, cancelled[0], recipient_ids=[recipient_id])
            else:
                lines = [f"❌ <b>Отменено задач: {len(cancelled)}</b>", ""]
                for i, e in enumerate(cancelled, 1):
                    lines.append(f"{i}. {escape(e.title)}")
                await self._send_to_recipients(
                    bot,
                    recipient_ids=[recipient_id],
                    text="\n".join(lines),
                    parse_mode="HTML",
                    event_name="TaskStateBatch",
                    event_id="CANCELLED",
                )

        if moved:
            if len(moved) == 1:
                await self._send_task_state(bot, moved[0], recipient_ids=[recipient_id])
            else:
                lines = [f"🔄 <b>Перемещено задач: {len(moved)}</b>", ""]
                for i, e in enumerate(moved, 1):
                    col = escape(e.column_title or "неизвестно")
                    lines.append(f"{i}. {escape(e.title)} → {col}")
                await self._send_to_recipients(
                    bot,
                    recipient_ids=[recipient_id],
                    text="\n".join(lines),
                    parse_mode="HTML",
                    event_name="TaskStateBatch",
                    event_id="COLUMN_CHANGED",
                )

        if updated:
            if len(updated) == 1:
                await self._send_task_state(bot, updated[0], recipient_ids=[recipient_id])
            else:
                lines = [f"✏️ <b>Обновлено задач: {len(updated)}</b>", ""]
                for i, e in enumerate(updated, 1):
                    lines.append(f"{i}. {escape(e.title)}")
                await self._send_to_recipients(
                    bot,
                    recipient_ids=[recipient_id],
                    text="\n".join(lines),
                    parse_mode="HTML",
                    event_name="TaskStateBatch",
                    event_id="UPDATED",
                )

    async def _send_task_state(
        self,
        bot: Bot,
        event: TaskStateEvent,
        recipient_ids: list[int] | None = None,
    ) -> None:
        deadline_str = event.deadline.strftime("%d.%m %H:%M") if event.deadline else "не указан"
        assignee_str = f"@{event.assignee_username}" if event.assignee_username else "не указан"

        if event.type == "CREATED":
            column_str = event.column_title or "без колонки"
            text = (
                f"✅ <b>Задача создана</b>\n\n"
                f"<b>{event.title}</b>\n"
                f"📂 Колонка: {column_str}\n"
                f"👤 Ответственный: {assignee_str}\n"
                f"⏰ Дедлайн: {deadline_str}"
            )
        elif event.type == "COLUMN_CHANGED":
            column_str = event.column_title or "неизвестно"
            text = (
                f"🔄 <b>Задача перемещена</b>\n\n"
                f"<b>{event.title}</b>\n"
                f"📂 Новая колонка: {column_str}"
            )
        elif event.type == "UPDATED":
            text = (
                f"✏️ <b>Задача обновлена</b>\n\n"
                f"<b>{event.title}</b>\n"
                f"👤 Ответственный: {assignee_str}\n"
                f"⏰ Дедлайн: {deadline_str}"
            )
        else:  # CANCELLED
            text = f"❌ <b>Задача отменена</b>\n\n<b>{event.title}</b>"

        await self._send_to_recipients(
            bot,
            recipient_ids=recipient_ids or event.recipient_telegram_ids,
            text=text,
            parse_mode="HTML",
            event_name="TaskStateEvent",
            event_id=event.task_id,
        )

    async def _handle_sync_notification(self, bot: Bot, event: BotSyncEvent) -> None:
        if event.type == "SYNC_PROMPT":
            if not event.recipient_telegram_ids:
                logger.warning("SYNC_PROMPT has no recipient_telegram_ids, skipping")
            else:
                for uid in event.recipient_telegram_ids:
                    try:
                        await bot.send_message(
                            chat_id=uid,
                            text="🌆 <b>Вечерняя синхронизация</b>\n\nОпишите одним сообщением, что вы сделали за день (каждую задачу — с новой строки).",
                            parse_mode="HTML",
                        )
                        sync_state.add_sync_user(uid)
                        logger.info("Sync prompt sent to userId={}", uid)
                    except TelegramAPIError as e:
                        logger.warning("Failed to send sync prompt to userId={}: {}", uid, e)

        elif event.type == "SYNC_SUMMARY":
            if not event.recipient_telegram_ids:
                logger.warning("SYNC_SUMMARY has no recipients")
                return
            text = _format_sync_summary(event.summary)
            kb = None
            if event.team_id and event.summary and event.summary.members:
                _summary_members_cache[event.team_id] = {
                    "overview": text,
                    "members": event.summary.members,
                }
                kb = build_sync_summary_keyboard(event.team_id)
            for manager_id in event.recipient_telegram_ids:
                try:
                    await bot.send_message(chat_id=manager_id, text=text, parse_mode="HTML", reply_markup=kb)
                except TelegramAPIError as e:
                    logger.warning("Failed to send sync summary to manager={}: {}", manager_id, e)

    async def _send_bot_notification(self, bot: Bot, event: BotNotificationEvent) -> None:
        task_title = escape(event.task_title or "Без названия")
        task_ref = f"\nID: <code>{escape(event.task_id)}</code>" if event.task_id else ""
        reply_markup = None

        if event.type == "DEADLINE":
            text = (
                "⏰ <b>Скоро дедлайн</b>\n\n"
                f"Задача: <b>{task_title}</b>"
                f"{task_ref}"
            )
        elif event.type == "STALE":
            text = (
                "🕓 <b>Задача давно без движения</b>\n\n"
                f"Задача: <b>{task_title}</b>"
                f"{task_ref}"
            )
        elif event.type == "ACHIEVEMENT":
            achievement_emoji = escape(event.achievement_emoji or "")
            achievement_name = escape(event.achievement_name or "достижение")
            xp_gained = event.xp_gained or 0
            new_total_xp = event.new_total_xp or 0
            text = (
                f"🏆 <b>Новая ачивка: «{achievement_emoji} {achievement_name}»</b>\n"
                f"+{xp_gained} XP · Теперь у тебя {new_total_xp} XP"
            )
        elif event.type == "LEVEL_UP":
            level_name = escape(event.new_level_name or "нового уровня")
            new_total_xp = event.new_total_xp or 0
            text = (
                f"🎉 Ты достиг уровня <b>{level_name}</b>!\n"
                f"⭐ XP: {new_total_xp}"
            )
        elif event.type == "COURSE_RECOMMENDATION":
            text = _format_course_recommendation(event)
        elif event.type == "MEETING_SUMMARY":
            text = _format_meeting_summary(event)
            reply_markup = _meeting_speaker_keyboard(event)
        elif event.type == "TEAM_CREATED":
            text = _format_team_created(event)
        elif event.type == "DEBUG":
            text = _format_debug(event)
        else:
            text = (
                "🔔 <b>Уведомление по задаче</b>\n\n"
                f"Задача: <b>{task_title}</b>"
                f"{task_ref}"
            )

        recipient_ids = event.recipient_telegram_ids
        if not recipient_ids and event.telegram_id is not None:
            recipient_ids = [event.telegram_id]

        await self._send_to_recipients(
            bot,
            recipient_ids=recipient_ids,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            event_name="BotNotificationEvent",
            event_id=event.task_id,
        )

    def _format_task_confirmation(self, event: TaskConfirmationEvent) -> str:
        prefix = "🤖 <b>Задача создана автоматически</b>" if event.auto_confirmed else "✅ <b>Задача создана</b>"
        lines = [prefix, "", f"<b>{escape(event.title)}</b>"]

        if event.column_title:
            lines.append(f"📂 Колонка: {escape(event.column_title)}")
        if event.assignee_username:
            lines.append(f"👤 Исполнитель: @{escape(event.assignee_username)}")
        if event.deadline:
            lines.append(f"⏰ Дедлайн: {_format_deadline(event.deadline)}")
        if event.description:
            lines.extend(["", escape(_clip(event.description, 500))])

        if event.task_id:
            lines.extend(["", f"ID: <code>{escape(event.task_id)}</code>"])
        return "\n".join(lines)

    async def _send_task_confirmation(self, bot: Bot, event: TaskConfirmationEvent) -> None:
        await self._send_to_recipients(
            bot,
            recipient_ids=event.recipient_telegram_ids,
            text=self._format_task_confirmation(event),
            parse_mode="HTML",
            event_name="TaskConfirmationEvent",
            event_id=event.task_id,
        )

    async def _send_to_recipients(
        self,
        bot: Bot,
        *,
        recipient_ids: list[int],
        text: str,
        parse_mode: str | None = None,
        reply_markup: object | None = None,
        event_name: str,
        event_id: str | None,
    ) -> None:
        seen: set[int] = set()
        delivered = 0
        send_kwargs = {"parse_mode": parse_mode} if parse_mode is not None else {}
        if reply_markup is not None:
            send_kwargs["reply_markup"] = reply_markup

        for recipient_id in recipient_ids:
            if recipient_id in seen:
                continue
            seen.add(recipient_id)
            try:
                await bot.send_message(chat_id=recipient_id, text=text, **send_kwargs)
                delivered += 1
            except TelegramAPIError as error:
                logger.warning(
                    "Failed to send {} {} to DM recipient {}: {}",
                    event_name,
                    event_id,
                    recipient_id,
                    error,
                )

        if not seen:
            logger.warning("{} {} has no DM recipients", event_name, event_id)
        elif delivered == 0:
            logger.warning("{} {} was not delivered to any DM recipient", event_name, event_id)


def _format_sync_summary(summary) -> str:
    if summary is None:
        return "📊 <b>Вечерняя синхронизация завершена</b>"

    responded_count = len(summary.responded_usernames)
    not_responded_count = len(summary.not_responded_usernames)
    excused = getattr(summary, "excused_entries", None) or []
    total = responded_count + not_responded_count + len(excused)

    lines = [
        "📊 <b>Итоги вечерней синхронизации</b>",
        "",
        f"Всего участников: {total}",
        f"✅ Отчитались: {responded_count}",
        f"❌ Не ответили: {not_responded_count}",
        f"🤒 На больничном/в отпуске: {len(excused)}",
    ]
    for entry in excused:
        lines.append(f"  • {escape(entry)}")
    lines += [
        "",
        f"📌 Задач закрыто: {summary.tasks_completed}",
        f"🆕 Новых задач: {summary.new_tasks_pending_approval}",
    ]

    members = getattr(summary, "members", None) or []
    if members:
        lines.append("")
        lines.append("Нажмите кнопку ниже, чтобы посмотреть детали по каждому участнику.")

    return "\n".join(lines)


def _format_deadline(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_DISPLAY_TZ).strftime("%d.%m %H:%M")


def _clip(value: str, max_length: int) -> str:
    stripped = value.strip()
    if len(stripped) <= max_length:
        return stripped
    return stripped[:max_length - 1].rstrip() + "…"


def _unique_ids(values: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _format_course_recommendation(event: "BotNotificationEvent") -> str:
    task_title = escape(event.task_title or "Без названия")
    lines = [
        f"<b>Задача просрочена: «{task_title}»</b>",
        "",
        "Вот материалы, которые помогут в будущем:",
        "",
    ]
    courses = event.courses or []
    for i, course in enumerate(courses, 1):
        title = escape(course.get("title") or "Курс")
        url = escape(course.get("url") or "")
        description = course.get("description") or ""
        desc_preview = escape(description[:100]) if description else ""
        lines.append(f"{i}. <b>{title}</b>")
        if desc_preview:
            lines.append(f"   {desc_preview}")
        if url:
            lines.append(f"   🔗 {url}")
        lines.append("")
    if not courses:
        lines.append("Подходящих курсов пока не найдено.")
    return "\n".join(lines)


def _format_meeting_summary(event: "BotNotificationEvent") -> str:
    title = escape(event.meeting_title or "Итоги встречи")
    summary = escape(_clip(event.meeting_summary or "Summary не сформировано.", 1800))
    lines = [
        "📝 <b>Summary встречи</b>",
        "",
        f"<b>{title}</b>",
        "",
        summary,
    ]

    tasks = [task for task in event.meeting_tasks if task]
    if tasks:
        lines.extend(["", "<b>Найденные задачи:</b>"])
        for task in tasks[:10]:
            lines.append(f"• {escape(_clip(task, 140))}")

    hints = [hint for hint in event.meeting_hints if hint]
    if hints:
        lines.extend(["", "<b>Подсказки:</b>"])
        for hint in hints[:5]:
            lines.append(f"• {escape(_clip(hint, 160))}")

    speakers = _meeting_speakers(event)
    if speakers:
        lines.extend(["", "<b>Говорящие:</b>"])
        for speaker in speakers[:6]:
            label = escape(speaker["label"])
            sample = escape(_clip(speaker["sample"], 140))
            lines.append(f"• <b>{label}</b>: «{sample}»")
        lines.extend(["", "Сопоставьте SPEAKER с участниками команды кнопками ниже."])

    if event.meeting_id:
        lines.extend(["", f"Meeting ID: <code>{escape(event.meeting_id)}</code>"])
    return "\n".join(lines)


def _meeting_speaker_keyboard(event: "BotNotificationEvent") -> InlineKeyboardMarkup | None:
    speakers = _meeting_speakers(event)
    if not event.meeting_id or not speakers:
        return None
    meeting_key = event.meeting_id.replace("-", "")
    rows = [
        [InlineKeyboardButton(
            text=f"👥 Сопоставить {speaker['label']}",
            callback_data=f"msel:{meeting_key}:{_speaker_num(speaker['label'])}",
        )]
        for speaker in speakers[:6]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _meeting_speakers(event: "BotNotificationEvent") -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for raw in event.meeting_speakers or []:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("speakerLabel") or raw.get("speaker_label") or "").strip()
        sample = str(raw.get("sample") or "").strip()
        if label and sample:
            result.append({"label": label, "sample": sample})
    return result


def _speaker_num(label: str) -> str:
    if "_" in label:
        return label.rsplit("_", 1)[-1]
    return label


def _format_team_created(event: "BotNotificationEvent") -> str:
    name = escape(event.team_name or "Команда")
    lines = [
        f"✅ <b>Команда «{name}» создана!</b>",
        f"Вы — менеджер 🎉",
        "",
        "Добавьте бота в Telegram-группу команды,",
        "затем свяжите её через «🔗 Привязать чат».",
    ]
    if event.invite_link:
        lines.extend(["", f"🔗 Ссылка для приглашения:\n{escape(event.invite_link)}"])
    return "\n".join(lines)


def _format_debug(event: "BotNotificationEvent") -> str:
    title = escape(event.task_title or "DEBUG")
    body = event.debug_text or ""
    return f"🐛 <b>[DEBUG] {title}</b>\n\n{body}"
