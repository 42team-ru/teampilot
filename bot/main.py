import asyncio
import contextlib
from typing import Any, Awaitable, Callable

from aiogram import Bot, BaseMiddleware, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject
from loguru import logger

from config import settings
from handlers.admin import router as admin_router
from handlers.courses import router as courses_router
from handlers.knowledge import router as knowledge_router
from handlers.auth import router as auth_router
from handlers.files import router as files_router
from handlers.group import router as group_router
from handlers.manager import router as manager_router
from handlers.member import router as member_router
from handlers.profile import router as profile_router
from handlers.registration import router as registration_router
from handlers.setup import router as setup_router
from handlers.sync import router as sync_router
from handlers.sync import sync_report_router
from handlers.tasks import router as tasks_router
from handlers.tasks_commands import router as tasks_commands_router
from handlers.upload import router as upload_router
from kafka.consumer import EventConsumer
from kafka.producer import EventProducer
from services.backend_error import BackendApiError
from services.http_client import http_client


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


class TelegramStaleCallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            message = str(e)
            if "query is too old" in message or "query ID is invalid" in message:
                logger.warning("Ignored stale Telegram callback answer: {}", message)
                return None
            raise


class BackendApiErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except BackendApiError as error:
            logger.warning(
                "Backend error shown to user: status={} detail={} trace_id={} instance={}",
                error.status,
                error.detail,
                error.trace_id,
                error.instance,
            )
            message = getattr(event, "message", None)
            callback = getattr(event, "callback_query", None)
            if callback is not None:
                message = callback.message

            if message is not None:
                await message.answer(error.user_message())
            if callback is not None:
                await callback.answer()
            return None


class UpdateTimingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        started = asyncio.get_running_loop().time()
        try:
            return await handler(event, data)
        finally:
            elapsed_ms = (asyncio.get_running_loop().time() - started) * 1000
            if elapsed_ms >= settings.UPDATE_SLOW_HANDLER_MS:
                logger.warning(
                    "Slow Telegram update handler: event_type={} elapsed_ms={:.1f}",
                    type(event).__name__,
                    elapsed_ms,
                )


async def monitor_event_loop_lag() -> None:
    interval = settings.EVENT_LOOP_LAG_INTERVAL_SECONDS
    warn_ms = settings.EVENT_LOOP_LAG_WARN_MS
    if interval <= 0 or warn_ms <= 0:
        return

    loop = asyncio.get_running_loop()
    expected = loop.time() + interval
    while True:
        await asyncio.sleep(interval)
        now = loop.time()
        lag_ms = max((now - expected) * 1000, 0)
        if lag_ms >= warn_ms:
            logger.warning("Event loop lag detected: lag_ms={:.1f}", lag_ms)
        expected = now + interval


async def main() -> None:
    session = AiohttpSession(timeout=settings.HTTP_TIMEOUT_SECONDS)
    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    producer = EventProducer(settings.KAFKA_BOOTSTRAP_SERVERS)
    dp.update.middleware(UpdateTimingMiddleware())
    dp.update.middleware(TelegramStaleCallbackMiddleware())
    dp.update.middleware(BackendApiErrorMiddleware())
    dp.update.middleware(KafkaProducerMiddleware(producer))

    # Order matters: registration guard first, setup before generic auth/group handlers.
    dp.include_router(registration_router)
    dp.include_router(setup_router)
    dp.include_router(admin_router)
    dp.include_router(courses_router)
    dp.include_router(manager_router)
    dp.include_router(member_router)
    dp.include_router(auth_router)
    dp.include_router(sync_router)
    dp.include_router(tasks_router)
    dp.include_router(tasks_commands_router)
    dp.include_router(upload_router)
    dp.include_router(files_router)
    dp.include_router(profile_router)
    dp.include_router(knowledge_router)
    dp.include_router(group_router)
    dp.include_router(sync_report_router)

    consumer = EventConsumer()
    consumer_task = asyncio.create_task(consumer.start(bot))
    loop_lag_task = asyncio.create_task(monitor_event_loop_lag())

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        consumer_task.cancel()
        loop_lag_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consumer_task
        with contextlib.suppress(asyncio.CancelledError):
            await loop_lag_task
        await asyncio.to_thread(producer.flush)
        await http_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
