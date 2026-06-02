import asyncio
from typing import Any, Awaitable, Callable

from aiogram import Bot, BaseMiddleware, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject
from loguru import logger

from config import settings
from handlers.auth import router as auth_router
from handlers.files import router as files_router
from handlers.group import router as group_router
from handlers.tasks import router as tasks_router
from kafka.consumer import EventConsumer
from kafka.producer import EventProducer


class KafkaProducerMiddleware(BaseMiddleware):
    def __init__(self, producer: EventProducer) -> None:
        self._producer = producer

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["producer"] = self._producer
        return await handler(event, data)


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    producer = EventProducer(settings.KAFKA_BOOTSTRAP_SERVERS)
    dp.update.middleware(KafkaProducerMiddleware(producer))

    # Order matters: specific routers first, most generic (group) last
    dp.include_router(auth_router)
    dp.include_router(tasks_router)
    dp.include_router(files_router)
    dp.include_router(group_router)

    consumer = EventConsumer()
    asyncio.create_task(consumer.start(bot))

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        producer.flush()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
