import logging
from typing import Any, Dict, Optional

import httpx

from .base import (
    DEFAULT_CODE_RESPONSE_SCHEMA,
    DEFAULT_CODE_SYSTEM_PROMPT,
    DEFAULT_CHAT_TIMEOUT,
    DEFAULT_CODE_GENERATION_TIMEOUT,
    DEFAULT_MODEL_LIST_TIMEOUT,
    LLMAdapter,
)

logger = logging.getLogger(__name__)


OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODELS_ENDPOINT = "https://api.openai.com/v1/models"


class OpenAIAdapter(LLMAdapter):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: Optional[str],
        model: str = "gpt-4o-mini",
        default_models: Optional[list[str]] = None,
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.model = model

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code using OpenAI models.

        Implements json_schema with fallback to json_object if unsupported.
        """
        await self.ensure_credentials()
        messages = kwargs.get("messages") or [
            {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        temperature = kwargs.get("temperature", 0.1)
        model = kwargs.get("model", self.model)

        response_format = kwargs.get("response_format") or {
            "type": "json_schema",
            "json_schema": {
                "name": "analysis_response",
                "schema": DEFAULT_CODE_RESPONSE_SCHEMA,
            },
        }

        logger.info(f"OpenAI generate_code: model={model}, temp={temperature}, format={response_format.get('type')}")

        request_body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": response_format,
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CODE_GENERATION_TIMEOUT) as client:
                response = await client.post(
                    OPENAI_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                try:
                    response.raise_for_status()
                    logger.debug("OpenAI API call successful")
                except httpx.HTTPStatusError as exc:
                    # Fallback: json_schema → json_object
                    if exc.response.status_code == 400 and response_format.get("type") == "json_schema":
                        logger.warning("OpenAI json_schema not supported, falling back to json_object")
                        request_body["response_format"] = {"type": "json_object"}
                        response = await client.post(
                            OPENAI_ENDPOINT,
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Content-Type": "application/json",
                            },
                            json=request_body,
                        )
                        response.raise_for_status()
                        logger.info("OpenAI fallback to json_object successful")
                    else:
                        logger.error(f"OpenAI API error: {exc.response.status_code} - {exc.response.text}")
                        raise

                payload = response.json()

        except httpx.RequestError as exc:
            logger.error(f"OpenAI request error: {exc}")
            raise

        content = payload["choices"][0]["message"]["content"]
        return {
            "raw": payload,
            "code": content,
            "usage": payload.get("usage", {}),
        }

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Chat with OpenAI models."""
        await self.ensure_credentials()
        temperature = kwargs.get("temperature", 0.3)
        model = kwargs.get("model", self.model)

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if "response_format" in kwargs:
            body["response_format"] = kwargs["response_format"]

        logger.info(f"OpenAI chat: model={model}, temp={temperature}, messages={len(messages)}")

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CHAT_TIMEOUT) as client:
                response = await client.post(
                    OPENAI_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
                logger.debug("OpenAI chat successful")

        except httpx.HTTPStatusError as exc:
            logger.error(f"OpenAI chat error: {exc.response.status_code} - {exc.response.text}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"OpenAI chat request error: {exc}")
            raise

        message = payload["choices"][0]["message"]
        return {"raw": payload, "message": message, "usage": payload.get("usage", {})}

    async def list_models(self) -> list[str]:
        """Fetch available models from OpenAI API with fallback to defaults."""
        try:
            await self.ensure_credentials()
        except RuntimeError:
            logger.debug("OpenAI credentials not configured, returning default models")
            return self.default_models

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_MODEL_LIST_TIMEOUT) as client:
                response = await client.get(
                    OPENAI_MODELS_ENDPOINT,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                models = [
                    item["id"]
                    for item in data.get("data", [])
                    if isinstance(item, dict) and item.get("id")
                ]
                logger.info(f"OpenAI: fetched {len(models)} models from API")
                return models or self.default_models
        except Exception as exc:
            logger.warning(f"Failed to fetch OpenAI models: {exc}, using defaults")
            return self.default_models
