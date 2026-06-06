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
        self._pending_created: dict[int, list[TaskStateEvent]] = {}
        self._confirmation_flush: dict[int, asyncio.Task] = {}
        self._created_flush: dict[int, asyncio.Task] = {}

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
            target = event.chat_id if event.chat_id is not None else event.user_id
            await bot.send_message(chat_id=target, text=event.text)

        elif topic == TOPIC_SUMMARY_SEND:
            event = SummarySendEvent.model_validate_json(payload)
            await bot.send_message(chat_id=event.chat_id, text=event.summary_text)

        elif topic == TOPIC_TASKS_STATE:
            event = TaskStateEvent.model_validate_json(payload)
            if event.type == "CREATED":
                await self._queue_created(bot, event)
            else:
                await self._send_task_state(bot, event)

        elif topic == TOPIC_BOTS_NOTIFICATIONS:
            event = BotNotificationEvent.model_validate_json(payload)
            await self._send_bot_notification(bot, event)

        elif topic == TOPIC_BOTS_TASKS:
            event = TaskConfirmationEvent.model_validate_json(payload)
            await self._queue_confirmation(bot, event)

    async def _queue_confirmation(self, bot: Bot, event: TaskConfirmationEvent) -> None:
        if event.chat_id is None:
            logger.warning("TaskConfirmationEvent {} has no chat_id", event.task_id)
            return
        chat_id = event.chat_id
        self._pending_confirmations.setdefault(chat_id, []).append(event)
        if chat_id not in self._confirmation_flush or self._confirmation_flush[chat_id].done():
            self._confirmation_flush[chat_id] = asyncio.create_task(
                self._flush_confirmations(bot, chat_id)
            )

    async def _flush_confirmations(self, bot: Bot, chat_id: int) -> None:
        await asyncio.sleep(_BATCH_WINDOW_SECS)
        events = self._pending_confirmations.pop(chat_id, [])
        if not events:
            return
        if len(events) == 1:
            await self._send_task_confirmation(bot, events[0])
            return
        auto = all(e.auto_confirmed for e in events)
        header = f"🤖 <b>Создано задач автоматически: {len(events)}</b>" if auto else f"<b>Создано задач: {len(events)}</b>"
        lines = [header, ""]
        for i, e in enumerate(events, 1):
            lines.append(f"{i}. <b>{escape(e.title)}</b>")
            if e.assignee_username:
                lines.append(f"   👤 @{escape(e.assignee_username)}")
            if e.deadline:
                lines.append(f"   ⏰ {_format_deadline(e.deadline)}")
        await bot.send_message(chat_id=chat_id, text="\n".join(lines), parse_mode="HTML")

    async def _queue_created(self, bot: Bot, event: TaskStateEvent) -> None:
        chat_id = event.chat_id
        self._pending_created.setdefault(chat_id, []).append(event)
        if chat_id not in self._created_flush or self._created_flush[chat_id].done():
            self._created_flush[chat_id] = asyncio.create_task(
                self._flush_created(bot, chat_id)
            )

    async def _flush_created(self, bot: Bot, chat_id: int) -> None:
        await asyncio.sleep(_BATCH_WINDOW_SECS)
        events = self._pending_created.pop(chat_id, [])
        if not events:
            return
        if len(events) == 1:
            await self._send_task_state(bot, events[0])
            return
        lines = [f"✅ <b>Создано задач: {len(events)}</b>", ""]
        for i, e in enumerate(events, 1):
            assignee_str = f"@{e.assignee_username}" if e.assignee_username else "не указан"
            deadline_str = e.deadline.strftime("%d.%m %H:%M") if e.deadline else "не указан"
            col_str = e.column_title or "без колонки"
            lines.append(f"{i}. <b>{escape(e.title)}</b>")
            lines.append(f"   📂 {col_str}  👤 {assignee_str}  ⏰ {deadline_str}")
        await bot.send_message(chat_id=chat_id, text="\n".join(lines), parse_mode="HTML")

    async def _send_task_state(self, bot: Bot, event: TaskStateEvent) -> None:
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
        else:  # CANCELLED
            text = f"❌ <b>Задача отменена</b>\n\n<b>{event.title}</b>"

        await bot.send_message(chat_id=event.chat_id, text=text, parse_mode="HTML")

    async def _send_task_proposal(self, bot: Bot, event: TaskProposeEvent) -> None:
        kb = build_task_keyboard(event.proposal_id)
        deadline_str = event.deadline.strftime("%d.%m %H:%M") if event.deadline else "не указан"
        text = (
            f"📋 <b>Новая задача</b>\n\n"
            f"<b>{event.task_title}</b>\n"
            f"👤 Ответственный: {event.assignee_name or 'не указан'}\n"
            f"⏰ Дедлайн: {deadline_str}"
        )
        await bot.send_message(
            chat_id=event.chat_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
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

        await self._send_with_fallback(
            bot,
            primary_chat_id=event.telegram_id,
            fallback_chat_id=event.chat_id,
            text=text,
        )

    async def _send_task_confirmation(self, bot: Bot, event: TaskConfirmationEvent) -> None:
        if event.chat_id is None:
            logger.warning("TaskConfirmationEvent {} has no chat_id", event.task_id)
            return

        prefix = "🤖 <b>Задача создана автоматически</b>" if event.auto_confirmed else "✅ <b>Задача создана</b>"
        lines = [
            prefix,
            "",
            f"<b>{escape(event.title)}</b>",
        ]

        if event.assignee_username:
            lines.append(f"Исполнитель: @{escape(event.assignee_username)}")
        if event.deadline:
            lines.append(f"Дедлайн: {_format_deadline(event.deadline)}")
        if event.description:
            lines.extend(["", escape(_clip(event.description, 500))])

        lines.extend(["", f"ID: <code>{escape(event.task_id)}</code>"])
        await bot.send_message(chat_id=event.chat_id, text="\n".join(lines))

    async def _send_with_fallback(
        self,
        bot: Bot,
        *,
        primary_chat_id: int | None,
        fallback_chat_id: int | None,
        text: str,
    ) -> None:
        if primary_chat_id is not None:
            try:
                await bot.send_message(chat_id=primary_chat_id, text=text)
                return
            except TelegramAPIError as error:
                logger.warning(
                    "Failed to send Kafka notification to primary chat {}: {}",
                    primary_chat_id,
                    error,
                )

        if fallback_chat_id is not None and fallback_chat_id != primary_chat_id:
            try:
                await bot.send_message(chat_id=fallback_chat_id, text=text)
                return
            except TelegramAPIError as error:
                logger.warning(
                    "Failed to send Kafka notification to fallback chat {}: {}",
                    fallback_chat_id,
                    error,
                )

        logger.warning(
            "Kafka notification was not delivered: primary_chat_id={} fallback_chat_id={}",
            primary_chat_id,
            fallback_chat_id,
        )


def _format_deadline(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_DISPLAY_TZ).strftime("%d.%m %H:%M")


def _clip(value: str, max_length: int) -> str:
    stripped = value.strip()
    if len(stripped) <= max_length:
        return stripped
    return stripped[:max_length - 1].rstrip() + "…"
