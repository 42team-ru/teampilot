"""
CLI-тулза для быстрой ручной проверки цепочек (LLaMA/Mistral).
Позволяет подавать текст напрямую или тестировать конкретный case из файла.

Примеры использования:
  uv run python debug_run.py "Петя, сделай докер-файл до четверга"
  uv run python debug_run.py "Ок займусь" --chain classifier
  uv run python debug_run.py --file tests/cases/case-001-frontend-bug.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from models import MessageBatchEvent, TaskCreateEvent, StatusChangeEvent

# Импорт цепочек
from main import _extract_tasks, _extract_statuses
from llm.chains import classifier_chain


def main():
    parser = argparse.ArgumentParser(description="Debug runner для LLM worker")
    parser.add_argument("text", nargs="?", help="Текст для обработки")
    parser.add_argument("--chain", choices=["all", "classifier", "task", "status"], default="all", help="Какую цепочку тестировать")
    parser.add_argument("--file", help="Путь к JSON файлу тест-кейса")
    args = parser.parse_args()

    # Если передан файл
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                case = json.load(f)
            
            logger.info(f"Запуск файла: {args.file}")
            logger.info(f"Описание: {case.get('description')}")
            
            # Конвертируем батч
            batch = MessageBatchEvent.model_validate(case["input_batch"])
            
            # Собираем текст
            text = "\n".join([
                f"[{msg.timestamp.strftime('%H:%M')}] {msg.username or msg.full_name}: {msg.text}"
                for msg in batch.messages
            ])
            logger.info("=== ИСХОДНЫЙ ТЕКСТ ===")
            print(text)
            print("======================\n")
            
            run_chains(text, batch, args.chain)
            return
            
        except Exception as e:
            logger.error(f"Ошибка чтения файла: {e}")
            sys.exit(1)

    # Если передан текст
    if args.text:
        text = args.text
        # Создаем фейковый батч для контекста
        batch = MessageBatchEvent(
            event_id="debug_batch",
            occurred_at=datetime.now(),
            team_id="00000000-0000-0000-0000-000000000001",
            messages=[],
            batch_start=datetime.now(),
            batch_end=datetime.now()
        )
        logger.info("=== ИСХОДНЫЙ ТЕКСТ ===")
        print(text)
        print("======================\n")
        run_chains(text, batch, args.chain)
        return

    parser.print_help()


def run_chains(text: str, batch: MessageBatchEvent, chain_type: str):
    if chain_type in ("all", "classifier"):
        logger.info("⏳ Запуск Classifier...")
        clf_output = classifier_chain.invoke({"messages": text})
        print(json.dumps(clf_output, indent=2, ensure_ascii=False))
        print()
        
    if chain_type in ("all", "task"):
        logger.info("⏳ Запуск Task Extractor...")
        task_events = _extract_tasks(batch, text)
        if task_events:
            print(json.dumps([e.model_dump() for e in task_events], indent=2, ensure_ascii=False, default=str))
        else:
            print("[] (Нет задач)")
        print()
        
    if chain_type in ("all", "status"):
        logger.info("⏳ Запуск Status Extractor...")
        status_events = _extract_statuses(batch, text)
        if status_events:
            print(json.dumps([e.model_dump() for e in status_events], indent=2, ensure_ascii=False, default=str))
        else:
            print("[] (Нет статусов)")
        print()


if __name__ == "__main__":
    main()
