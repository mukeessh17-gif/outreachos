"""The only module that sends prompts to the configured AI provider."""

import json
import logging
import os
import random
import re
import time
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from sqlalchemy import text

from week2.db import get_engine

load_dotenv()

# Keep the model name in one constant and use only a key with no billing enabled.
MODEL = "gemini-3.8-flash"
logger = logging.getLogger("outreachos.llm")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _record_call(
    org_id: int,
    purpose: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    success: bool,
) -> None:
    with get_engine().begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )
        connection.execute(
            text(
                "INSERT INTO llm_calls "
                "(org_id, purpose, model, input_tokens, output_tokens, latency_ms, success) "
                "VALUES (:org_id, :purpose, :model, :input_tokens, :output_tokens, "
                ":latency_ms, :success)"
            ),
            {
                "org_id": org_id,
                "purpose": purpose[:60],
                "model": MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "success": success,
            },
        )


def ask_llm(
    prompt: str,
    *,
    org_id: int = 1,
    purpose: str = "demo",
    max_output_tokens: int = 2048,
) -> tuple[str, int, int]:
    """Call Gemini with bounded 429 retries and record every provider attempt."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "fake-gemini-key":
        raise RuntimeError("Set a real GEMINI_API_KEY in .env to use AI features.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    for attempt in range(3):
        started = time.monotonic()
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                ),
            )
            output = response.text
            if not output:
                raise RuntimeError("The AI provider returned an empty response.")
            usage = getattr(response, "usage_metadata", None)
            input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            is_rate_limited = status_code == 429 or "429" in str(error)
            _record_call(
                org_id,
                purpose,
                0,
                0,
                int((time.monotonic() - started) * 1000),
                False,
            )
            if is_rate_limited and attempt < 2:
                time.sleep((2**attempt) + random.uniform(0, 0.25))
                continue
            logger.error("AI provider call failed (error type: %s)", type(error).__name__)
            raise RuntimeError("The AI provider call failed; see server logs for the error type.") from error
        _record_call(
            org_id,
            purpose,
            input_tokens,
            output_tokens,
            int((time.monotonic() - started) * 1000),
            True,
        )
        return output, input_tokens, output_tokens
    raise RuntimeError("The AI provider call failed after retries.")


def request_validated(
    prompt: str,
    response_model: type[SchemaT],
    *,
    org_id: int,
    purpose: str,
    max_output_tokens: int = 2048,
) -> tuple[SchemaT, int, int]:
    """Parse model output into a Pydantic schema; retry invalid JSON once."""
    validation_error: Exception | None = None
    total_input = 0
    total_output = 0
    for attempt in range(2):
        retry_note = ""
        if validation_error is not None:
            retry_note = (
                "\nYour previous answer failed schema validation. Return only valid JSON "
                "matching the requested schema."
            )
        raw, input_tokens, output_tokens = ask_llm(
            prompt + retry_note,
            org_id=org_id,
            purpose=purpose,
            max_output_tokens=max_output_tokens,
        )
        total_input += input_tokens
        total_output += output_tokens
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw, flags=re.IGNORECASE)
        try:
            return response_model.model_validate(json.loads(cleaned)), total_input, total_output
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            validation_error = error
    raise ValueError(f"AI response did not match {response_model.__name__} after one retry.") from validation_error
