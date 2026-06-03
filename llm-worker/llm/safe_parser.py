import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from loguru import logger


class SafeJsonOutputParser(BaseOutputParser[Any]):
    """
    Парсер JSON с фоллбеками для слабых моделей (LLaMA/Mistral),
    которые любят оборачивать JSON в markdown, даже если их просят этого не делать.
    """

    def parse(self, text: str) -> Any:
        text = text.strip()

        # 1. Пробуем распарсить как есть
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Убираем markdown обёртку (```json ... ```)
        # Ищем всё, что между первой и последней тройной обратной кавычкой
        match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            clean_text = match.group(1).strip()
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError:
                pass

        # 3. Пытаемся найти первый попавшийся JSON-подобный блок (массив или объект)
        # Ищем от первой [ или { до последней ] или }
        start_idx = text.find('[')
        start_obj_idx = text.find('{')
        
        # Выбираем, что встретилось раньше (массив или объект)
        if start_idx != -1 and (start_obj_idx == -1 or start_idx < start_obj_idx):
            end_idx = text.rfind(']')
            if end_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(text[start_idx:end_idx+1])
                except json.JSONDecodeError:
                    pass
        elif start_obj_idx != -1:
            end_idx = text.rfind('}')
            if end_idx != -1 and end_idx > start_obj_idx:
                try:
                    return json.loads(text[start_obj_idx:end_idx+1])
                except json.JSONDecodeError:
                    pass

        # 4. Если всё упало - логируем raw output
        logger.error(f"SafeJsonOutputParser failed to parse LLM output: {text!r}")
        # Чтобы не ронять весь пайплайн, возвращаем пустой словарь (или поднимаем ошибку - зависит от цепочки)
        # Для наших задач безопаснее кинуть Exception, чтобы fallback обработался на уровне выше, 
        # но так как в main.py у нас try-except вокруг валидации pydantic, можем кидать ValueError
        raise OutputParserException(f"Failed to parse json. Output: {text!r}")

    @property
    def _type(self) -> str:
        return "safe_json_output_parser"
