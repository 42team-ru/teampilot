import asyncio

from aiogram import Bot
from confluent_kafka import Consumer
from loguru import logger

from config import settings
from kafka.topics import TOPIC_REMINDER_SEND, TOPIC_SUMMARY_SEND, TOPIC_TASK_PROPOSE
from keyboards.task import build_task_keyboard
from models.events import ReminderSendEvent, SummarySendEvent, TaskProposeEvent


class EventConsumer:
    TOPICS = [TOPIC_TASK_PROPOSE, TOPIC_REMINDER_SEND, TOPIC_SUMMARY_SEND]

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
                msg = consumer.poll(timeout=0.1)
                if msg is None:
                    await asyncio.sleep(0)
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
