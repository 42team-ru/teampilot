"""
ML Test Runner

Два режима запуска:

  MOCK (по умолчанию):
    uv run python -m tests.runner
    — Валидирует только структуру тест-кейсов. LLM не вызывается, токены не тратятся.

  LIVE (реальная проверка качества):
    LLM_TESTS=1 uv run python -m tests.runner
    — Прогоняет каждый кейс через настоящую LLaMA. Важно: требует запущенного Ollama.
"""
import json
import os
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger

# ── Глобальный флаг ─────────────────────────────────────────────────────────
# Изолирован в тестовой структуре. Нигде в основном коде не используется.
RUN_LIVE_LLM: bool = os.getenv("LLM_TESTS", "").lower() in ("1", "true", "yes")

# Порог схожести строк для fuzzy-матчинга (title, task_hint)
FUZZY_PASS = 0.85
FUZZY_FAIL = 0.35


def _fuzzy_sim(a: str, b: str) -> float:
    """Возвращает степень схожести двух строк от 0.0 до 1.0."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ── Runner ────────────────────────────────────────────────────────────────────

class MLTestRunner:
    """
    Инструмент для прогона тест-кейсов экстракции.

    В MOCK-режиме (по умолчанию) только проверяет структуру JSON-кейсов.
    В LIVE-режиме (LLM_TESTS=1) реально вызывает LLaMA через process_batch().
    """

    def __init__(self, cases_path: str, results_path: str) -> None:
        self.cases_path = Path(cases_path)
        self.results_path = Path(results_path)
        self.results_path.mkdir(parents=True, exist_ok=True)

    def load_cases(self, target: str) -> List[Dict[str, Any]]:
        path = self.cases_path / target
        cases = []
        
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cases.extend(data)
                else:
                    cases.append(data)
        elif path.is_dir():
            for p in sorted(path.glob("*.json")):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        cases.extend(data)
                    else:
                        cases.append(data)
        return cases

    def run_suite(self, filename: str) -> None:
        cases = self.load_cases(filename)

        if RUN_LIVE_LLM:
            logger.warning("⚡ LIVE MODE: Вызывается настоящая LLaMA. Токены будут потрачены.")
            logger.warning("   Убедись, что Ollama запущена и модель загружена.")
            # Импортируем ТОЛЬКО здесь — чтобы не создавать Kafka Producer в mock-режиме
            from models import MessageBatchEvent, TaskCreateEvent, StatusChangeEvent
            from main import process_batch
            self._live_imports = {
                "MessageBatchEvent": MessageBatchEvent,
                "TaskCreateEvent": TaskCreateEvent,
                "StatusChangeEvent": StatusChangeEvent,
                "process_batch": process_batch,
            }
        else:
            logger.info("🔒 MOCK MODE: LLM не вызывается. Только структурная валидация.")
            logger.info("   Для реального теста качества: LLM_TESTS=1 python tests/runner.py")

        logger.info(f"Запуск набора: {filename} ({len(cases)} кейсов)\n")

        results = []
        stats = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "ERROR": 0, "SKIPPED": 0}

        for case in cases:
            if RUN_LIVE_LLM:
                result = self._run_live(case)
            else:
                result = self._run_mock(case)

            stats[result["status"]] = stats.get(result["status"], 0) + 1
            self._log_result(result)
            results.append(result)

        self._print_summary(stats, len(cases))

        # Сохраняем отчёт в Markdown
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_path / f"report_{timestamp}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Отчёт о тестировании LLM Worker\n\n")
            f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Режим:** {'LIVE (LLaMA)' if RUN_LIVE_LLM else 'MOCK (Structural)'}\n\n")
            
            for res in results:
                emoji = {"PASS": "✅", "PARTIAL": "🟡", "FAIL": "❌", "ERROR": "💥", "SKIPPED": "⏭️"}.get(res["status"], "?")
                f.write(f"## {emoji} {res.get('case_id', 'Unknown Case')}\n\n")
                
                desc = res.get('description', res.get('note', ''))
                if desc:
                    f.write(f"**Описание:** {desc}\n\n")
                
                if res.get("error"):
                    f.write(f"**Ошибка:** {res['error']}\n\n")
                    f.write("---\n\n")
                    continue
                    
                if "text" in res:
                    f.write("### Входной текст (Input)\n")
                    f.write("```text\n")
                    f.write(res["text"] + "\n")
                    f.write("```\n\n")
                
                if "expected" in res:
                    f.write("### Ожидаемый результат\n")
                    f.write("```json\n")
                    f.write(json.dumps(res["expected"], indent=2, ensure_ascii=False) + "\n")
                    f.write("```\n\n")
                
                if "actual" in res:
                    f.write("### Ответ нейронки (Actual)\n")
                    f.write("```json\n")
                    f.write(json.dumps(res["actual"], indent=2, ensure_ascii=False) + "\n")
                    f.write("```\n\n")
                    
                f.write("### Наша оценка\n")
                f.write(f"**Статус:** {res['status']}\n\n")
                if res.get("details"):
                    f.write(f"**Детали:** {res['details']}\n\n")
                    
                f.write("---\n\n")

        logger.info(f"Отчёт сохранён: {report_path}")

    # ── Режимы ─────────────────────────────────────────────────────────────

    def _run_mock(self, case: Dict) -> Dict:
        """Валидирует структуру кейса. LLM не вызывается."""
        case_id = case.get("id", "?")
        try:
            assert "id" in case, "Нет поля 'id'"
            assert "description" in case, "Нет поля 'description'"
            assert "input_batch" in case, "Нет поля 'input_batch'"
            assert "expected_output" in case, "Нет поля 'expected_output'"
            assert case["expected_output"]["type"] in (
                "task", "status", "none", "tasks"
            ), f"Неизвестный тип: {case['expected_output']['type']}"
            return {
                "case_id": case_id,
                "status": "SKIPPED",
                "note": f"MOCK — структура OK: {case.get('description', '')}",
            }
        except AssertionError as e:
            return {"case_id": case_id, "status": "ERROR", "error": f"Плохая структура: {e}"}

    def _run_live(self, case: Dict) -> Dict:
        """Реально вызывает LLaMA через process_batch() и сравнивает результат."""
        case_id = case.get("id", "?")
        expected = case["expected_output"]
        MessageBatchEvent = self._live_imports["MessageBatchEvent"]
        process_batch = self._live_imports["process_batch"]

        try:
            batch = MessageBatchEvent.model_validate(case["input_batch"])
            # Извлекаем текст для судьи
            text = "\n".join([f"[{m.timestamp.strftime('%H:%M')}] {m.username}: {m.text}" for m in batch.messages])
            
            actual_events = process_batch(batch)
            status, details = self._compare(actual_events, expected, text)
            return {
                "case_id": case_id,
                "description": case.get("description", ""),
                "text": text,
                "expected": expected,
                "actual": [e.model_dump() for e in actual_events],
                "status": status,
                "details": details,
            }
        except Exception as e:
            logger.error(f"Исключение в кейсе {case_id}: {e}")
            return {"case_id": case_id, "status": "ERROR", "error": str(e)}

    # ── Сравнение ──────────────────────────────────────────────────────────

    def _compare(self, actual_events: list, expected: Dict, text: str = "") -> Tuple[str, str]:
        """
        Гибридное сравнение:
          PASS    — тип совпал + детерминированные поля совпали + (fuzzy > 0.85 ИЛИ судья сказал EQUIVALENT)
          PARTIAL — есть расхождения (≤1 проблема) ИЛИ судья сказал PARTIAL
          FAIL    — критические расхождения ИЛИ судья сказал DIFFERENT
        """
        TaskCreateEvent = self._live_imports["TaskCreateEvent"]
        StatusChangeEvent = self._live_imports["StatusChangeEvent"]

        exp_type = expected["type"]
        exp_data = expected.get("data", {})

        # ── none ──────────────────────────────────────────────────────────
        if exp_type == "none":
            if not actual_events:
                return "PASS", "Корректно вернул пустой результат"
            return "FAIL", f"Ожидался пустой результат, получено {len(actual_events)} событий"

        # ── tasks (multiple) ──────────────────────────────────────────────────────
        if exp_type == "tasks":
            task_events = [e for e in actual_events if isinstance(e, TaskCreateEvent)]
            if len(task_events) != len(exp_data):
                return "FAIL", f"Ожидалось {len(exp_data)} задач, получено {len(task_events)}"
            
            # Упрощенная проверка для мульти-тасок: проверяем что все expected_assignee найдены
            expected_assignees = {t.get("assignee", "").lower() for t in exp_data if t.get("assignee")}
            actual_assignees = {(e.assignee or "").lower() for e in task_events}
            
            missing = expected_assignees - actual_assignees
            if missing:
                return "PARTIAL", f"Найдены все задачи, но потеряны assignee: {missing}"
                
            return "PASS", f"Корректно извлечено {len(task_events)} задач"

        # ── task (single) ─────────────────────────────────────────────────────────
        if exp_type == "task":
            task_events = [e for e in actual_events if isinstance(e, TaskCreateEvent)]
            if not task_events:
                return "FAIL", "Ожидалось task-событие, LLM ничего не вернула"

            event = task_events[0]
            issues = []

            if "title" in exp_data:
                sim = _fuzzy_sim(event.title, exp_data["title"])
                if sim < FUZZY_FAIL:
                    issues.append(f"title: ожидалось «{exp_data['title']}», получено «{event.title}»")
                elif sim < FUZZY_PASS:
                    verdict, reason = self._llm_judge(text, exp_data["title"], event.title)
                    if verdict == "DIFFERENT":
                        issues.append(f"title (судья): {reason}")
                    elif verdict == "PARTIAL":
                        issues.append(f"title (судья - неточность): {reason}")

            if "assignee" in exp_data and exp_data["assignee"]:
                got = (event.assignee or "").lower()
                want = exp_data["assignee"].lower()
                if want not in got and got not in want:
                    issues.append(
                        f"assignee: ожидалось «{exp_data['assignee']}», получено «{event.assignee}»"
                    )

            if "priority" in exp_data and event.priority != exp_data["priority"]:
                issues.append(
                    f"priority: ожидалось «{exp_data['priority']}», получено «{event.priority}»"
                )

            if not issues:
                return "PASS", "Все ключевые поля совпадают"
            if len(issues) == 1:
                return "PARTIAL", issues[0]
            return "FAIL", "; ".join(issues)

        # ── status ────────────────────────────────────────────────────────
        if exp_type == "status":
            status_events = [e for e in actual_events if isinstance(e, StatusChangeEvent)]
            if not status_events:
                return "FAIL", "Ожидалось status-событие, LLM ничего не вернула"

            event = status_events[0]
            issues = []

            if "action" in exp_data and event.action != exp_data["action"]:
                issues.append(
                    f"action: ожидалось «{exp_data['action']}», получено «{event.action}»"
                )

            if "task_hint" in exp_data:
                sim = _fuzzy_sim(event.task_hint, exp_data["task_hint"])
                if sim < FUZZY_FAIL:
                    issues.append(f"task_hint: ожидалось «{exp_data['task_hint']}», получено «{event.task_hint}»")
                elif sim < FUZZY_PASS:
                    verdict, reason = self._llm_judge(text, exp_data["task_hint"], event.task_hint)
                    if verdict == "DIFFERENT":
                        issues.append(f"task_hint (судья): {reason}")
                    elif verdict == "PARTIAL":
                        issues.append(f"task_hint (судья - неточность): {reason}")

            if not issues:
                return "PASS", "Все ключевые поля совпадают"
            if len(issues) == 1:
                return "PARTIAL", issues[0]
            return "FAIL", "; ".join(issues)

        return "FAIL", f"Неизвестный тип expected: {exp_type}"

    # ── LLM Судья ──────────────────────────────────────────────────────────

    def _llm_judge(self, text: str, expected: str, actual: str) -> Tuple[str, str]:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from llm.safe_parser import SafeJsonOutputParser
        from settings import settings

        prompt = ChatPromptTemplate.from_messages([("system", """You are a strict semantic equivalence checker.
Given:
  - Original chat dialogue
  - Expected task title: "{expected_title}"
  - Actual task title from AI: "{actual_title}"

Decide if the actual title captures the SAME TASK as expected.
Minor wording differences are OK. Different meaning = NOT OK.

RESPOND ONLY WITH VALID JSON:
{{"verdict": "EQUIVALENT"|"PARTIAL"|"DIFFERENT", "reason": "short explanation"}}"""),
        ("human", "Dialogue:\n{dialogue}")])

        chain = prompt | ChatOpenAI(
            model=settings.LLM_CHEAP_MODEL,
            base_url=settings.LLM_API_BASE,
            api_key=settings.LLM_API_KEY,
            temperature=0.0
        ) | SafeJsonOutputParser()

        try:
            res = chain.invoke({"expected_title": expected, "actual_title": actual, "dialogue": text})
            return res.get("verdict", "DIFFERENT"), res.get("reason", "unknown")
        except Exception as e:
            return "PARTIAL", f"judge error: {e}"

    # ── Вывод ──────────────────────────────────────────────────────────────

    def _log_result(self, result: Dict) -> None:
        status = result.get("status", "?")
        case_id = result.get("case_id", "?")
        emoji = {
            "PASS": "✅", "PARTIAL": "🟡", "FAIL": "❌",
            "ERROR": "💥", "SKIPPED": "⏭️",
        }.get(status, "?")
        detail = result.get("details", result.get("note", result.get("error", "")))
        logger.info(f"  {emoji} [{status:7s}] {case_id}: {detail}")

    def _print_summary(self, stats: Dict, total: int) -> None:
        logger.info("")
        logger.info("══════════════════════════════════════════════")

        if not RUN_LIVE_LLM:
            logger.info(f"  MOCK MODE — {total} кейсов прошли структурную валидацию")
            logger.info("  Для проверки качества LLM: LLM_TESTS=1 python tests/runner.py")
        else:
            live = total - stats.get("SKIPPED", 0)
            passed = stats.get("PASS", 0)
            partial = stats.get("PARTIAL", 0)
            failed = stats.get("FAIL", 0)
            errors = stats.get("ERROR", 0)
            score = (passed + partial * 0.5) / live * 100 if live > 0 else 0.0

            logger.info(
                f"  RESULTS: {passed}/{live} PASS | {partial} PARTIAL | "
                f"{failed} FAIL | {errors} ERROR"
            )
            logger.info(f"  Score: {score:.1f}%")

        logger.info("══════════════════════════════════════════════")


# ── Точка входа ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Можно передать имя файла или директорию: python tests/runner.py advanced_cases
    # Если передать '.', будут запущены все файлы из tests/cases
    target_path = sys.argv[1] if len(sys.argv) > 1 else "."
    runner = MLTestRunner("tests/cases", "tests/results")
    runner.run_suite(target_path)
