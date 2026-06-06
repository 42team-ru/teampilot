import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from loguru import logger


class SafeJsonOutputParser(BaseOutputParser[Any]):

    def parse(self, text: str) -> Any:
        text = text.strip()
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        logger.error(f"SafeJsonOutputParser failed to parse LLM output: {text!r}")
        raise OutputParserException(f"Failed to parse json. Output: {text!r}")

    @property
    def _type(self) -> str:
        return "safe_json_output_parser"
