from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message
from loguru import logger

from kafka.producer import EventProducer
from kafka.topics import TOPIC_MESSAGES_RAW
from models.events import RawMessageEvent

router = Router()


# NOTE: Requires Privacy Mode disabled in BotFather (Bot Settings → Group Privacy → Turn off)
# Without this, the handler will not fire for regular group messages.
@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group_message(message: Message, producer: EventProducer) -> None:
    logger.info(
        f"[MSG] chat={message.chat.id} user={message.from_user.id} "
        f"({message.from_user.full_name}): {message.text[:80]!r}"
    )
    event = RawMessageEvent(
        message_id=message.message_id,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        text=message.text or "",
        timestamp=datetime.now(timezone.utc),
    )
    await producer.publish(TOPIC_MESSAGES_RAW, event)
    logger.debug(f"[MSG] published to Kafka: message_id={message.message_id}")
