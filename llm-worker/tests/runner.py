import json
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger
from models import MessageBatchEvent
from main import process_batch

class MLTestRunner:
    """
    Инструмент для прогона тестов экстракции без использования Kafka.
    """
    
    def __init__(self, cases_path: str, results_path: str):
        self.cases_path = Path(cases_path)
        self.results_path = Path(results_path)
        self.results_path.mkdir(parents=True, exist_ok=True)

    def load_cases(self, filename: str) -> List[Dict[str, Any]]:
        with open(self.cases_path / filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run_suite(self, filename: str):
        cases = self.load_cases(filename)
        results = []
        
        logger.info(f"Запуск тестового набора: {filename} ({len(cases)} кейсов)")
        
        for case in cases:
            case_id = case['id']
            logger.info(f"Тестируем: {case_id} - {case['description']}")
            
            # Валидируем входной батч через модель Pydantic
            try:
                batch = MessageBatchEvent.model_validate(case['input_batch'])
                
                # Прогоняем через нашу основную логику (уже отрефакторенную!)
                actual_events = process_batch(batch)
                
                # Сохраняем результат
                results.append({
                    "case_id": case_id,
                    "expected": case['expected_output'],
                    "actual": [e.model_dump() for e in actual_events],
                    "status": "PASS" if self._compare(actual_events, case['expected_output']) else "FAIL"
                })
            except Exception as e:
                logger.error(f"Ошибка в кейсе {case_id}: {e}")
                results.append({"case_id": case_id, "error": str(e), "status": "ERROR"})

        # Записываем отчет
        report_path = self.results_path / f"report_{filename}"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Отчет сохранен в {report_path}")

    def _compare(self, actual, expected) -> bool:
        """
        Базовое сравнение результатов. 
        На хакатоне пока проверяем наличие событий, завтра добавим семантику.
        """
        if expected['type'] == 'none':
            return len(actual) == 0
        return len(actual) > 0

if __name__ == "__main__":
    runner = MLTestRunner("tests/cases", "tests/results")
    runner.run_suite("basic_extraction.json")
