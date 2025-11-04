from typing import Any, Dict, Optional

import httpx

from .base import DEFAULT_CODE_SYSTEM_PROMPT, LLMAdapter


class DeepSeekAdapter(LLMAdapter):
    name = "deepseek"

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: str,
        default_models: Optional[list[str]] = None,
    ):
        super().__init__(api_key=api_key, default_models=default_models)
        self.base_url = base_url.rstrip("/") or "https://api.deepseek.com"
        self.chat_endpoint = f"{self.base_url}/chat/completions"
        self.models_endpoint = f"{self.base_url}/models"

    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        payload = {
            "model": kwargs.get("model", self.default_models[0] if self.default_models else "deepseek-chat"),
            "messages": kwargs.get("messages")
            or [
                {
                    "role": "system",
                    "content": DEFAULT_CODE_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.1),
        }

        async with httpx.AsyncClient(timeout=40.0) as client:
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

        message = data["choices"][0]["message"]
        return {
            "raw": data,
            "code": message.get("content", ""),
            "usage": data.get("usage", {}),
        }

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        if not messages or messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
                *messages,
            ]
        payload = {
            "model": kwargs.get("model", self.default_models[0] if self.default_models else "deepseek-chat"),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        async with httpx.AsyncClient(timeout=40.0) as client:
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
        return {
            "raw": data,
            "message": data["choices"][0]["message"],
            "usage": data.get("usage", {}),
        }

    async def list_models(self) -> list[str]:
        try:
            await self.ensure_credentials()
        except RuntimeError:
            return self.default_models
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    self.models_endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
                models = [item["id"] for item in payload.get("data", []) if item.get("id")]
                return models or self.default_models
        except Exception:
            return self.default_models
