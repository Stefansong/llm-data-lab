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


class QwenAdapter(LLMAdapter):
    name = "qwen"

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: str,
        default_models: Optional[list[str]] = None,
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.base_url = base_url.rstrip("/")
        self.text_endpoint = f"{self.base_url}/api/v1/services/aigc/text-generation/generation"
        self.chat_endpoint_url = f"{self.base_url}/api/v1/services/aigc/text-generation/generation"
        self.models_endpoint = f"{self.base_url}/api/v1/models"

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code using Qwen (通义千问) models.

        Handles Qwen's nested response structure with robust error checking.
        """
        await self.ensure_credentials()
        model = kwargs.get("model", self.default_models[0] if self.default_models else "qwen-plus")

        logger.info(f"Qwen generate_code: model={model}")

        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            },
            "parameters": {"result_format": "json"},
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CODE_GENERATION_TIMEOUT) as client:
                response = await client.post(
                    self.text_endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Qwen API error: {exc.response.status_code} - {exc.response.text}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"Qwen request error: {exc}")
            raise

        # Parse nested response structure with validation
        output = data.get("output")
        if not output:
            logger.error(f"Qwen response missing 'output' field: {data}")
            raise ValueError("Invalid Qwen response: missing 'output' field")

        choices = output.get("choices")
        if not choices or not isinstance(choices, list):
            logger.error(f"Qwen response missing valid 'choices' field: {output}")
            raise ValueError("Invalid Qwen response: missing or invalid 'choices' field")

        # Extract content from first choice
        text = ""
        if choices:
            first_choice = choices[0]
            # Try message.content first (standard format)
            text = first_choice.get("message", {}).get("content", "")
            # Fallback to text field (older format)
            if not text:
                text = first_choice.get("text", "")

        if not text:
            logger.warning("Qwen returned empty content")

        logger.debug(f"Qwen returned {len(text)} characters")

        return {"raw": data, "code": text, "usage": data.get("usage", {})}

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Chat with Qwen models.

        Handles Qwen's nested response structure with robust error checking.
        """
        await self.ensure_credentials()
        model = kwargs.get("model", self.default_models[0] if self.default_models else "qwen-plus")

        if not messages or messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
                *messages,
            ]

        logger.info(f"Qwen chat: model={model}, messages={len(messages)}")

        payload = {
            "model": model,
            "input": {"messages": messages},
            "parameters": {"result_format": "json"},
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CHAT_TIMEOUT) as client:
                response = await client.post(
                    self.chat_endpoint_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Qwen chat API error: {exc.response.status_code} - {exc.response.text}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"Qwen chat request error: {exc}")
            raise

        # Parse nested response structure with validation
        output = data.get("output")
        if not output:
            logger.error(f"Qwen chat response missing 'output' field: {data}")
            raise ValueError("Invalid Qwen response: missing 'output' field")

        choices = output.get("choices")
        if not choices or not isinstance(choices, list):
            logger.error(f"Qwen chat response missing valid 'choices' field: {output}")
            # Return empty message instead of crashing
            return {
                "raw": data,
                "message": {"role": "assistant", "content": ""},
                "usage": data.get("usage", {}),
            }

        message = choices[0].get("message", {}) if choices else {"role": "assistant", "content": ""}
        logger.debug(f"Qwen chat returned message with {len(message.get('content', ''))} characters")

        return {"raw": data, "message": message, "usage": data.get("usage", {})}

    async def list_models(self) -> list[str]:
        """Fetch available models from Qwen API with fallback to defaults.

        Handles multiple possible response formats from DashScope API.
        """
        try:
            await self.ensure_credentials()
        except RuntimeError:
            logger.debug("Qwen credentials not configured, returning default models")
            return self.default_models

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_MODEL_LIST_TIMEOUT) as client:
                response = await client.get(
                    self.models_endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()

                # Try multiple possible response structures
                data = payload.get("data") or payload.get("models") or []
                if not isinstance(data, list):
                    logger.warning(f"Qwen models response has unexpected structure: {payload}")
                    return self.default_models

                # Extract model names (may be under 'model' or 'id' field)
                models = []
                for item in data:
                    if isinstance(item, dict):
                        model_name = item.get("model") or item.get("id")
                        if model_name:
                            models.append(model_name)

                logger.info(f"Qwen: fetched {len(models)} models from API")
                return models or self.default_models

        except Exception as exc:
            logger.warning(f"Failed to fetch Qwen models: {exc}, using defaults")
            return self.default_models
