import json
import logging
from typing import Any, Dict, Optional

import httpx

from .base import (
    DEFAULT_CODE_SYSTEM_PROMPT,
    DEFAULT_CHAT_TIMEOUT,
    DEFAULT_CODE_GENERATION_TIMEOUT,
    DEFAULT_MODEL_LIST_TIMEOUT,
    LLMAdapter,
)

logger = logging.getLogger(__name__)

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

# Enhanced JSON prompt for Anthropic (since it doesn't support response_format)
JSON_ENFORCEMENT_SUFFIX = (
    "\n\nCRITICAL: Your response MUST be a valid JSON object. "
    "Do not include any markdown code fences (```), explanations, or text outside the JSON. "
    "Start your response with { and end with }. Validate that your response is parseable JSON before sending."
)


class AnthropicAdapter(LLMAdapter):
    name = "anthropic"

    def __init__(
        self, *, api_key: Optional[str], model: str = "claude-3-sonnet-20240229", default_models: Optional[list[str]] = None
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.model = model

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code using Claude models.

        Since Anthropic doesn't support response_format, we enhance the system prompt
        to strictly enforce JSON output and validate the response.
        """
        await self.ensure_credentials()
        system_prompt = kwargs.get("system_prompt", DEFAULT_CODE_SYSTEM_PROMPT)
        # Enhance prompt to enforce JSON output
        system_prompt += JSON_ENFORCEMENT_SUFFIX

        temperature = kwargs.get("temperature", 0.1)
        model = kwargs.get("model", self.model)

        logger.info(f"Anthropic generate_code: model={model}, temp={temperature}")

        request_body = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CODE_GENERATION_TIMEOUT) as client:
                response = await client.post(
                    ANTHROPIC_ENDPOINT,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Anthropic API error: {exc.response.status_code} - {exc.response.text}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"Anthropic request error: {exc}")
            raise

        content = "".join(item.get("text", "") for item in payload["content"])

        # Validate JSON output
        try:
            json.loads(content)
            logger.debug("Anthropic returned valid JSON")
        except json.JSONDecodeError as exc:
            logger.warning(f"Anthropic returned invalid JSON: {exc}. Attempting to extract JSON...")
            # Try to extract JSON from markdown fences
            content = self._extract_json_from_text(content)

        return {"raw": payload, "code": content, "usage": payload.get("usage", {})}

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text that may contain markdown fences or extra content."""
        import re

        # Try to find JSON within markdown fences
        fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if fence_match:
            logger.info("Extracted JSON from markdown fence")
            return fence_match.group(1).strip()

        # Try to find JSON object by finding matching braces
        start = text.find('{')
        if start != -1:
            # Find matching closing brace
            brace_count = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        extracted = text[start:i+1]
                        try:
                            json.loads(extracted)
                            logger.info("Extracted JSON by brace matching")
                            return extracted
                        except json.JSONDecodeError:
                            pass

        logger.warning("Could not extract valid JSON, returning original text")
        return text

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Chat with Claude models.

        Handles response_format hint by enhancing system prompt for JSON output.
        """
        await self.ensure_credentials()
        system_prompt = kwargs.get("system_prompt", DEFAULT_CODE_SYSTEM_PROMPT)

        # If JSON output is requested, enhance prompt
        if kwargs.get("response_format", {}).get("type") in ["json_object", "json_schema"]:
            system_prompt += JSON_ENFORCEMENT_SUFFIX
            logger.debug("Enhanced Anthropic chat prompt for JSON output")

        temperature = kwargs.get("temperature", 0.3)
        model = kwargs.get("model", self.model)

        logger.info(f"Anthropic chat: model={model}, temp={temperature}, messages={len(messages)}")

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CHAT_TIMEOUT) as client:
                response = await client.post(
                    ANTHROPIC_ENDPOINT,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": kwargs.get("max_tokens", 2048),
                        "temperature": temperature,
                        "system": system_prompt,
                        "messages": messages,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Anthropic API error: {exc.response.status_code} - {exc.response.text}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"Anthropic request error: {exc}")
            raise

        content = "".join(item.get("text", "") for item in payload["content"])

        # Validate JSON if requested
        if kwargs.get("response_format"):
            try:
                json.loads(content)
                logger.debug("Anthropic chat returned valid JSON")
            except json.JSONDecodeError:
                logger.warning("Anthropic chat returned invalid JSON, attempting extraction...")
                content = self._extract_json_from_text(content)

        return {
            "raw": payload,
            "message": {"role": "assistant", "content": content},
            "usage": payload.get("usage", {}),
        }

    async def list_models(self) -> list[str]:
        return self.default_models
