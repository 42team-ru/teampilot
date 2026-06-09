import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from loguru import logger


def _escape_literal_control_chars(text: str) -> str:
    """Escape literal control characters inside JSON string values."""
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and in_string:
            result.append(c)
            i += 1
            if i < len(text):
                result.append(text[i])
            i += 1
            continue
        if c == '"':
            in_string = not in_string
            result.append(c)
        elif in_string and c == "\n":
            result.append("\\n")
        elif in_string and c == "\r":
            result.append("\\r")
        elif in_string and c == "\t":
            result.append("\\t")
        else:
            result.append(c)
        i += 1
    return "".join(result)


def _try_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fixed = _escape_literal_control_chars(text)
    return json.loads(fixed)


class SafeJsonOutputParser(BaseOutputParser[Any]):

    def parse(self, text: str) -> Any:
        text = text.strip()
        # Strip complete <thinking>...</thinking> and <output>...</output> blocks
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
        text = re.sub(r"<output>(.*?)</output>", r"\1", text, flags=re.DOTALL).strip()

        try:
            return _try_parse(text)
        except json.JSONDecodeError:
            pass

        # Markdown code block
        match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return _try_parse(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Model forgot to close </thinking> — find the first { or [ and parse from there
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            idx = text.find(start_char)
            if idx != -1:
                last_idx = text.rfind(end_char)
                if last_idx > idx:
                    candidate = text[idx:last_idx + 1]
                    try:
                        return _try_parse(candidate)
                    except json.JSONDecodeError:
                        pass

        logger.error(f"SafeJsonOutputParser failed to parse LLM output: {text!r}")
        raise OutputParserException(f"Failed to parse json. Output: {text!r}")

    @property
    def _type(self) -> str:
        return "safe_json_output_parser"
