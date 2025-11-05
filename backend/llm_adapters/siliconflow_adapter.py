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


class SiliconFlowAdapter(LLMAdapter):
    name = "siliconflow"

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: str,
        default_models: Optional[list[str]] = None,
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.base_url = base_url.rstrip("/")
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
        self.models_endpoint = f"{self.base_url}/v1/models"

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code using SiliconFlow models.

        Implements robust fallback logic for response_format similar to OpenAI adapter.
        """
        await self.ensure_credentials()
        model = kwargs.get("model", self.default_models[0] if self.default_models else "siliconflow-chat")
        messages = kwargs.get("messages") or [
            {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        temperature = kwargs.get("temperature", 0.1)

        logger.info(f"SiliconFlow generate_code: model={model}, temp={temperature}")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        # Try with response_format if provided
        response_format = kwargs.get("response_format")
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CODE_GENERATION_TIMEOUT) as client:
                response = await client.post(
                    self.chat_endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                logger.debug("SiliconFlow API call successful")

        except httpx.HTTPStatusError as exc:
            # Fallback: If response_format is not supported, retry without it
            if response_format and exc.response.status_code in {400, 422}:
                logger.warning(
                    f"SiliconFlow doesn't support response_format, retrying without it. "
                    f"Status: {exc.response.status_code}"
                )
                payload.pop("response_format", None)
                async with httpx.AsyncClient(timeout=DEFAULT_CODE_GENERATION_TIMEOUT) as client:
                    response = await client.post(
                        self.chat_endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    logger.info("SiliconFlow fallback successful (without response_format)")
            else:
                logger.error(f"SiliconFlow API error: {exc.response.status_code} - {exc.response.text}")
                raise

        except httpx.RequestError as exc:
            logger.error(f"SiliconFlow request error: {exc}")
            raise

        message = data["choices"][0]["message"]
        return {
            "raw": data,
            "code": message.get("content", ""),
            "usage": data.get("usage", {}),
        }

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Chat with SiliconFlow models.

        Implements robust fallback logic for response_format similar to OpenAI adapter.
        """
        await self.ensure_credentials()
        if not messages or messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
                *messages,
            ]

        model = kwargs.get("model", self.default_models[0] if self.default_models else "siliconflow-chat")
        temperature = kwargs.get("temperature", 0.2)

        logger.info(f"SiliconFlow chat: model={model}, temp={temperature}, messages={len(messages)}")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        # If caller requests JSON response (OpenAI-compatible), pass it through
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
            logger.debug("SiliconFlow chat: using response_format")

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CHAT_TIMEOUT) as client:
                try:
                    response = await client.post(
                        self.chat_endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    logger.debug("SiliconFlow chat successful")

                except httpx.HTTPStatusError as exc:
                    # Fallback: if server doesn't support response_format, retry without it
                    if "response_format" in payload and exc.response is not None and exc.response.status_code in {400, 422}:
                        logger.warning(
                            f"SiliconFlow chat doesn't support response_format, retrying without it. "
                            f"Status: {exc.response.status_code}"
                        )
                        payload.pop("response_format", None)
                        response = await client.post(
                            self.chat_endpoint,
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )
                        response.raise_for_status()
                        data = response.json()
                        logger.info("SiliconFlow chat fallback successful")
                    else:
                        logger.error(f"SiliconFlow chat error: {exc.response.status_code} - {exc.response.text}")
                        raise

        except httpx.RequestError as exc:
            logger.error(f"SiliconFlow chat request error: {exc}")
            raise

        return {
            "raw": data,
            "message": data["choices"][0]["message"],
            "usage": data.get("usage", {}),
        }

    async def list_models(self) -> list[str]:
        """Fetch available models from SiliconFlow API with fallback to defaults."""
        try:
            await self.ensure_credentials()
        except RuntimeError:
            logger.debug("SiliconFlow credentials not configured, returning default models")
            return self.default_models

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_MODEL_LIST_TIMEOUT) as client:
                response = await client.get(
                    self.models_endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
                models = [item.get("id") for item in payload.get("data", []) if item.get("id")]
                logger.info(f"SiliconFlow: fetched {len(models)} models from API")
                return models or self.default_models
        except Exception as exc:
            logger.warning(f"Failed to fetch SiliconFlow models: {exc}, using defaults")
            return self.default_models
