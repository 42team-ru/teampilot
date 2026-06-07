from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from keyboards.sync import build_active_tasks_keyboard, build_reject_choice_keyboard, build_sync_draft_keyboard
from services import sync_service
from services import sync_state as sync_state_service
from services.http_client import http_client
from states.sync import SyncEditStates, SyncRejectStates

router = Router()
sync_report_router = Router()


# ---------------------------------------------------------------------------
# Admin test commands
# ---------------------------------------------------------------------------

@router.message(Command("test_sync"))
async def cmd_test_sync(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    await message.answer("⏳ Запускаю вечерний синк...")
    await sync_service.trigger_sync()
    await message.answer("✅ Синк запущен — бот отправил промпт во все активные чаты")


@router.message(Command("test_sync_summary"))
async def cmd_test_sync_summary(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    await message.answer("⏳ Закрываю окно синка и отправляю summary...")
    await sync_service.trigger_summary()
    await message.answer("✅ Summary отправлен менеджерам")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _call_sync_confirm(
    chat_id: int,
    telegram_user_id: int,
    action: str,
    item_index: int = 0,
    new_task_title: str | None = None,
    task_id: str | None = None,
) -> None:
    payload = {
        "chatId": chat_id,
        "telegramUserId": telegram_user_id,
        "action": action,
        "itemIndex": item_index,
        "newTaskTitle": new_task_title,
        "taskId": task_id,
    }
    await http_client.post(f"{settings.BACKEND_URL}/sync/confirm", json=payload)


async def _submit_next_pending(user_id: int, state: FSMContext, reply_msg: Message) -> None:
    data = await state.get_data()
    pending = data.get("pending_sync_tasks", [])
    total = data.get("total_sync_tasks", 0)
    if not pending:
        return
    next_text = pending[0]
    remaining = pending[1:]
    done_count = total - len(pending)
    await state.update_data(pending_sync_tasks=remaining)
    await reply_msg.answer(f"⏳ Обрабатываю задачу {done_count + 1}/{total}...")
    resp = await http_client.post(
        f"{settings.BACKEND_URL}/sync/submit",
        json={"telegramUserId": user_id, "text": next_text},
        headers={"X-Bot-Secret": settings.BOT_SECRET},
    )
    if resp.status_code != 204:
        await reply_msg.answer(f"❌ Ошибка при отправке: {escape(next_text[:60])}")


# ---------------------------------------------------------------------------
# Sync draft callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("sync_confirm:"))
async def sync_confirm_all(callback: CallbackQuery, state: FSMContext) -> None:
    group_chat_id = int(callback.data.split(":", 1)[1])
    await _call_sync_confirm(group_chat_id, callback.from_user.id, "CONFIRM_ALL")
    await callback.message.edit_text(
        callback.message.html_text + "\n\n✅ <b>Задача подтверждена</b>",
        reply_markup=None,
        parse_mode="HTML",
    )
    await callback.answer("✅ Задача подтверждена")
    await _submit_next_pending(callback.from_user.id, state, callback.message)


@router.callback_query(F.data.startswith("sync_reject:"))
async def sync_reject(callback: CallbackQuery) -> None:
    group_chat_id = int(callback.data.split(":", 1)[1])
    await _call_sync_confirm(group_chat_id, callback.from_user.id, "REJECT")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Синк отклонён")
    await callback.message.answer(
        "Что сделать с этой задачей?",
        reply_markup=build_reject_choice_keyboard(group_chat_id),
    )


# ---------------------------------------------------------------------------
# Reject choice callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("sync_pick_list:"))
async def sync_pick_list(callback: CallbackQuery) -> None:
    group_chat_id = int(callback.data.split(":", 1)[1])
    try:
        resp = await http_client.get(
            f"{settings.BACKEND_URL}/sync/active-tasks",
            params={"telegramUserId": callback.from_user.id},
            headers={"X-Bot-Secret": settings.BOT_SECRET},
        )
    except Exception:
        await callback.answer("Не удалось загрузить задачи", show_alert=True)
        return
    if resp.status_code != 200:
        await callback.answer("Не удалось загрузить задачи", show_alert=True)
        return
    tasks = resp.json()
    try:
        if not tasks:
            await callback.message.edit_text(
                "У вас нет активных задач.",
                reply_markup=build_reject_choice_keyboard(group_chat_id),
            )
        else:
            await callback.message.edit_text(
                "Выберите задачу, которую вы выполнили:",
                reply_markup=build_active_tasks_keyboard(tasks, group_chat_id),
            )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("sync_pick_task:"))
async def sync_pick_task(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    group_chat_id = int(parts[1])
    raw = parts[2]
    # UUID пришёл без дефисов — восстанавливаем формат 8-4-4-4-12
    task_id = f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    await _call_sync_confirm(group_chat_id, callback.from_user.id, "COMPLETE_TASK", task_id=task_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ Задача отмечена как выполненная")
    await _submit_next_pending(callback.from_user.id, state, callback.message)


@router.callback_query(F.data.startswith("sync_create_new:"))
async def sync_create_new(callback: CallbackQuery, state: FSMContext) -> None:
    group_chat_id = int(callback.data.split(":", 1)[1])
    await state.update_data(group_chat_id=group_chat_id)
    await state.set_state(SyncRejectStates.waiting_for_new_title)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await callback.message.answer(
        "Введите название новой задачи или /skip чтобы пропустить:"
    )


@router.callback_query(F.data.startswith("sync_skip_new:"))
async def sync_skip_new(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Пропущено")
    await _submit_next_pending(callback.from_user.id, state, callback.message)


@router.callback_query(F.data.startswith("sync_prop_approve:"))
async def sync_prop_approve(callback: CallbackQuery) -> None:
    proposal_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/approve-proposal",
            json={"proposalId": proposal_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Задача принята и создана</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("✅ Задача создана")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут принимать задачи", show_alert=True)
    elif resp.status_code == 404:
        await callback.answer("⚠️ Предложение уже обработано", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при принятии задачи", show_alert=True)


@router.callback_query(F.data.startswith("sync_prop_reject:"))
async def sync_prop_reject(callback: CallbackQuery) -> None:
    proposal_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/reject-proposal",
            json={"proposalId": proposal_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n❌ <b>Задача отклонена</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("Задача отклонена")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут отклонять задачи", show_alert=True)
    elif resp.status_code == 404:
        await callback.answer("⚠️ Предложение уже обработано", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при отклонении задачи", show_alert=True)


@router.callback_query(F.data.startswith("sync_task_approve:"))
async def sync_task_approve(callback: CallbackQuery) -> None:
    task_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/approve-task",
            json={"taskId": task_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Задача принята</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("✅ Задача принята")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут принимать задачи", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при одобрении задачи", show_alert=True)


@router.callback_query(F.data.startswith("sync_task_reject:"))
async def sync_task_reject_approval(callback: CallbackQuery) -> None:
    task_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/reject-task",
            json={"taskId": task_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n❌ <b>Задача отклонена</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("Задача отклонена")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут отклонять задачи", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при отклонении задачи", show_alert=True)


@router.message(SyncRejectStates.waiting_for_new_title)
async def sync_new_task_input(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    group_chat_id = data.get("group_chat_id")
    if text.lower() in {"/skip", "skip"}:
        await state.set_state(None)
        await message.answer("Задача не создана.")
        await _submit_next_pending(message.from_user.id, state, message)
        return
    await state.set_state(None)
    resp = await http_client.post(
        f"{settings.BACKEND_URL}/sync/confirm",
        json={
            "chatId": group_chat_id,
            "telegramUserId": message.from_user.id,
            "action": "CREATE_NEW",
            "itemIndex": 0,
            "newTaskTitle": text,
            "taskId": None,
        },
    )
    if resp.status_code == 204:
        await message.answer(
            f"✅ Задача <b>{escape(text)}</b> создана и отправлена на подтверждение менеджеру.",
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Не удалось создать задачу, попробуйте позже.")
    await _submit_next_pending(message.from_user.id, state, message)


# ---------------------------------------------------------------------------
# Edit callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("sync_edit:"))
async def sync_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    group_chat_id = int(parts[1])
    await state.update_data(group_chat_id=group_chat_id)
    await state.set_state(SyncEditStates.waiting_for_new_title)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Напишите или переформулируйте задачу:")
    await callback.answer()


@router.message(SyncEditStates.waiting_for_new_title)
async def sync_edit_new_title(message: Message, state: FSMContext) -> None:
    new_text = (message.text or "").strip()
    if not new_text:
        await message.answer("Текст не может быть пустым:")
        return
    # Выходим из FSM-состояния, но НЕ чистим данные (pending_sync_tasks должен сохраниться)
    await state.set_state(None)
    await message.answer("⏳ Обрабатываю...")
    resp = await http_client.post(
        f"{settings.BACKEND_URL}/sync/submit",
        json={"telegramUserId": message.from_user.id, "text": new_text},
        headers={"X-Bot-Secret": settings.BOT_SECRET},
    )
    if resp.status_code != 204:
        await message.answer("❌ Ошибка при отправке, попробуйте ещё раз.")


# ---------------------------------------------------------------------------
# Multi-message sync report handler
# ---------------------------------------------------------------------------

class _IsSyncUser(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return (
            message.from_user is not None
            and sync_state_service.is_in_sync(message.from_user.id)
        )


@sync_report_router.message(F.chat.type == "private", _IsSyncUser())
async def handle_sync_report(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if text.lower() in {"/ready", "ready"}:
        tasks = sync_state_service.remove_sync_user(user_id)
        if not tasks:
            await message.answer("Нет задач для отчёта. Напишите хотя бы одну.")
            return
        total = len(tasks)
        await state.update_data(pending_sync_tasks=tasks[1:], total_sync_tasks=total)
        await message.answer(f"⏳ Обрабатываю задачу 1/{total}...")
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/submit",
            json={"telegramUserId": user_id, "text": tasks[0]},
            headers={"X-Bot-Secret": settings.BOT_SECRET},
        )
        if resp.status_code != 204:
            await message.answer(f"❌ Ошибка при отправке: {escape(tasks[0][:60])}")
        return

    sync_state_service.add_task_message(user_id, text)
    task_count = len(sync_state_service.get_task_messages(user_id))
    await message.answer(
        f"📝 <b>Задача {task_count} принята:</b> {escape(text[:120])}\n\n"
        f"Добавь следующую или отправь /ready",
        parse_mode="HTML",
    )
