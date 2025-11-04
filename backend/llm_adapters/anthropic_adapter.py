from typing import Any, Dict, Optional

import httpx

from .base import DEFAULT_CODE_SYSTEM_PROMPT, LLMAdapter


ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


class AnthropicAdapter(LLMAdapter):
    name = "anthropic"

    def __init__(
        self, *, api_key: Optional[str], model: str = "claude-3-sonnet-20240229", default_models: Optional[list[str]] = None
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.model = model

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        system_prompt = kwargs.get("system_prompt", DEFAULT_CODE_SYSTEM_PROMPT)
        temperature = kwargs.get("temperature", 0.1)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_ENDPOINT,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()

        content = "".join(item.get("text", "") for item in payload["content"])
        return {"raw": payload, "code": content, "usage": payload.get("usage", {})}

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        system_prompt = kwargs.get("system_prompt", DEFAULT_CODE_SYSTEM_PROMPT)
        temperature = kwargs.get("temperature", 0.3)
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.post(
                ANTHROPIC_ENDPOINT,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            payload = response.json()

        content = "".join(item.get("text", "") for item in payload["content"])
        return {
            "raw": payload,
            "message": {"role": "assistant", "content": content},
            "usage": payload.get("usage", {}),
        }

    async def list_models(self) -> list[str]:
        return self.default_models
