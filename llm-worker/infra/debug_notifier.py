"""
Debug notifier: публикует отладочные сообщения в bots.notifications
чтобы админ видел всё что происходит в ЛС.
Активируется через DEBUG_MODE=true + DEBUG_ADMIN_IDS=id1,id2
"""
import json
from loguru import logger
from confluent_kafka import Producer

from settings import settings

_TOPIC = "bots.notifications"
_MAX_TEXT = 3900  # Telegram limit ~4096, оставляем запас

_producer: Producer | None = None


def _get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
    return _producer


def _send(title: str, body: str) -> None:
    if not settings.DEBUG_MODE:
        return
    admin_ids = settings.DEBUG_ADMIN_IDS
    if not admin_ids:
        return
    payload = {
        "type": "DEBUG",
        "recipient_telegram_ids": admin_ids,
        "task_title": title,
        "debug_text": body[:_MAX_TEXT],
    }
    try:
        producer = _get_producer()
        producer.produce(_TOPIC, value=json.dumps(payload).encode(), key=b"debug")
        producer.poll(0)
    except Exception as e:
        logger.warning("Debug notify publish failed: {}", e)


def notify_batch_received(batch_id: str, n_messages: int, text: str) -> None:
    body = f"<b>ID:</b> <code>{batch_id[:8]}</code>\n<b>Сообщений:</b> {n_messages}\n\n{text[:1500]}"
    _send("Батч получен", body)


def notify_classification(batch_id: str, has_task: bool, conf_task: float,
                          has_status: bool, conf_status: float,
                          has_decision: bool, conf_decision: float) -> None:
    lines = [f"<b>Батч:</b> <code>{batch_id[:8]}</code>", ""]
    lines.append(f"{'✅' if has_task else '❌'} Задача: {conf_task:.0%}")
    lines.append(f"{'✅' if has_status else '❌'} Смена статуса: {conf_status:.0%}")
    lines.append(f"{'✅' if has_decision else '❌'} Решение: {conf_decision:.0%}")
    _send("Классификация батча", "\n".join(lines))


def notify_tasks_extracted(batch_id: str, tasks: list) -> None:
    if not tasks:
        _send("Тасков не найдено", f"Батч: <code>{batch_id[:8]}</code>")
        return
    lines = [f"<b>Батч:</b> <code>{batch_id[:8]}</code>  |  найдено: {len(tasks)}", ""]
    for i, t in enumerate(tasks, 1):
        lines.append(f"<b>{i}. {t.title}</b>")
        if t.assignee_id:
            lines.append(f"   👤 assignee_id: {t.assignee_id}")
        if t.deadline:
            lines.append(f"   ⏰ deadline: {t.deadline}")
        if t.column_id:
            lines.append(f"   📂 column_id: {t.column_id}")
        lines.append(f"   🤖 уверенность: {t.confidence:.0%}")
        lines.append("")
    _send("Тасков создано", "\n".join(lines))


def notify_statuses_extracted(batch_id: str, statuses: list) -> None:
    if not statuses:
        _send("Смен статуса не найдено", f"Батч: <code>{batch_id[:8]}</code>")
        return
    lines = [f"<b>Батч:</b> <code>{batch_id[:8]}</code>  |  найдено: {len(statuses)}", ""]
    for i, s in enumerate(statuses, 1):
        lines.append(f"<b>{i}. {s.action}</b>")
        if s.task_id:
            lines.append(f"   🆔 task_id: <code>{s.task_id}</code>")
        if s.assignee_id:
            lines.append(f"   👤 assignee_id: {s.assignee_id}")
        if s.column_id:
            lines.append(f"   📂 column_id: {s.column_id}")
        lines.append("")
    _send("Смены статуса", "\n".join(lines))


def notify_transcript(file_id: str, char_count: int, preview: str) -> None:
    body = (
        f"<b>file_id:</b> <code>{file_id[:16]}</code>\n"
        f"<b>Символов:</b> {char_count}\n\n"
        f"{preview[:2000]}"
    )
    _send("Транскрипция готова", body)


def notify_no_results(batch_id: str) -> None:
    _send(
        "Батч без результатов",
        f"Батч <code>{batch_id[:8]}</code> — LLM не нашла ни тасков, ни смен статуса.",
    )
