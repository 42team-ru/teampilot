import asyncio
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from confluent_kafka import Consumer
from loguru import logger

from config import settings
from kafka.topics import (
    TOPIC_BOTS_NOTIFICATIONS,
    TOPIC_BOTS_TASKS,
    TOPIC_REMINDER_SEND,
    TOPIC_SUMMARY_SEND,
    TOPIC_TASK_PROPOSE,
    TOPIC_TASKS_STATE,
)
from keyboards.task import build_task_keyboard
from models.events import (
    BotNotificationEvent,
    ReminderSendEvent,
    SummarySendEvent,
    TaskConfirmationEvent,
    TaskProposeEvent,
    TaskStateEvent,
)

_DISPLAY_TZ = timezone(timedelta(hours=3))
_BATCH_WINDOW_SECS = 3


class EventConsumer:
    TOPICS = [
        TOPIC_TASK_PROPOSE,
        TOPIC_REMINDER_SEND,
        TOPIC_SUMMARY_SEND,
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

        if topic == TOPIC_TASK_PROPOSE:
            event = TaskProposeEvent.model_validate_json(payload)
            await self._send_task_proposal(bot, event)

        elif topic == TOPIC_REMINDER_SEND:
            event = ReminderSendEvent.model_validate_json(payload)
            target = event.user_id if event.task_id is not None else event.chat_id or event.user_id
            await bot.send_message(chat_id=target, text=event.text)

        elif topic == TOPIC_SUMMARY_SEND:
            event = SummarySendEvent.model_validate_json(payload)
            await bot.send_message(chat_id=event.chat_id, text=event.summary_text)

        elif topic == TOPIC_TASKS_STATE:
            event = TaskStateEvent.model_validate_json(payload)
            if event.type != "CREATED":
                await self._queue_state(bot, event)

        elif topic == TOPIC_BOTS_NOTIFICATIONS:
            event = BotNotificationEvent.model_validate_json(payload)
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
            await self._send_to_recipients(
                bot,
                recipient_ids=[recipient_id],
                text=self._format_task_confirmation(events[0]),
                parse_mode="HTML",
                event_name="TaskConfirmationEvent",
                event_id=events[0].task_id,
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

    async def _send_task_proposal(self, bot: Bot, event: TaskProposeEvent) -> None:
        kb = build_task_keyboard(event.proposal_id)
        deadline_str = event.deadline.strftime("%d.%m %H:%M") if event.deadline else "не указан"
        text = (
            f"📋 <b>Новая задача</b>\n\n"
            f"<b>{event.task_title}</b>\n"
            f"👤 Ответственный: {event.assignee_name or 'не указан'}\n"
            f"⏰ Дедлайн: {deadline_str}"
        )
        await self._send_to_recipients(
            bot,
            recipient_ids=event.recipient_telegram_ids,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
            event_name="TaskProposeEvent",
            event_id=event.proposal_id,
        )

    async def _send_bot_notification(self, bot: Bot, event: BotNotificationEvent) -> None:
        task_title = escape(event.task_title or "Без названия")
        task_ref = f"\nID: <code>{escape(event.task_id)}</code>" if event.task_id else ""

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
