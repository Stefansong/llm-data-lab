from typing import Any, Dict, Optional

import httpx

from .base import DEFAULT_CODE_SYSTEM_PROMPT, LLMAdapter


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
        await self.ensure_credentials()
        model = kwargs.get("model", self.default_models[0] if self.default_models else "qwen-plus")
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
        async with httpx.AsyncClient(timeout=40.0) as client:
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
        output = data.get("output") or {}
        choices = output.get("choices") or []
        text = ""
        if choices:
            text = choices[0].get("message", {}).get("content", "") or choices[0].get("text", "")
        return {"raw": data, "code": text, "usage": data.get("usage", {})}

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        model = kwargs.get("model", self.default_models[0] if self.default_models else "qwen-plus")
        if not messages or messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": DEFAULT_CODE_SYSTEM_PROMPT},
                *messages,
            ]
        payload = {
            "model": model,
            "input": {"messages": messages},
            "parameters": {"result_format": "json"},
        }
        async with httpx.AsyncClient(timeout=40.0) as client:
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
        output = data.get("output") or {}
        choices = output.get("choices") or []
        message = choices[0].get("message", {}) if choices else {"role": "assistant", "content": ""}
        return {"raw": data, "message": message, "usage": data.get("usage", {})}

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
                data = payload.get("data") or payload.get("models") or []
                models = [item.get("model") or item.get("id") for item in data if isinstance(item, dict)]
                return [m for m in models if m] or self.default_models
        except Exception:
            return self.default_models
