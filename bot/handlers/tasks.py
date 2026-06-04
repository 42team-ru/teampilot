from aiogram import F, Router
from aiogram.types import CallbackQuery

from kafka.producer import EventProducer
from kafka.topics import TOPIC_STATUS_CHANGED, TOPIC_TASK_CONFIRMED, TOPIC_TASK_REJECTED
from models.events import StatusChangedEvent, TaskConfirmedEvent, TaskRejectedEvent

router = Router()

_STATUS_LABELS = {
    "in_progress": "🔄 В работе",
    "done": "✅ Готово",
    "blocked": "🚫 Заблокировано",
}


@router.callback_query(F.data.startswith("task_confirm:"))
async def task_confirm(callback: CallbackQuery, producer: EventProducer) -> None:
    proposal_id = callback.data.split(":", 1)[1]

    event = TaskConfirmedEvent(
        proposal_id=proposal_id,
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
    )
    await producer.publish(TOPIC_TASK_CONFIRMED, event, key=proposal_id)

    await callback.message.edit_text(
        callback.message.html_text + "\n\n✅ <b>Задача создана</b>",
        reply_markup=None,
        parse_mode="HTML",
    )
    await callback.answer("✅ Задача создана")


@router.callback_query(F.data.startswith("task_reject:"))
async def task_reject(callback: CallbackQuery, producer: EventProducer) -> None:
    proposal_id = callback.data.split(":", 1)[1]

    event = TaskRejectedEvent(
        proposal_id=proposal_id,
        user_id=callback.from_user.id,
    )
    await producer.publish(TOPIC_TASK_REJECTED, event, key=proposal_id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Пропущено")


@router.callback_query(F.data.startswith("status:"))
async def change_status(callback: CallbackQuery, producer: EventProducer) -> None:
    # Format: "status:{task_id}:{new_status}"
    _, task_id, new_status = callback.data.split(":", 2)

    event = StatusChangedEvent(
        task_id=task_id,
        user_id=callback.from_user.id,
        new_status=new_status,
    )
    await producer.publish(TOPIC_STATUS_CHANGED, event, key=task_id)

    label = _STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"Статус изменён: {label}")
