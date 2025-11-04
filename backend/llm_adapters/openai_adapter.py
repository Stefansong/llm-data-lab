from typing import Any, Dict, Optional

import httpx

from .base import (
    DEFAULT_CODE_RESPONSE_SCHEMA,
    DEFAULT_CODE_SYSTEM_PROMPT,
    LLMAdapter,
)


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
        await self.ensure_credentials()
        messages = kwargs.get("messages") or [
            {
                "role": "system",
                "content": DEFAULT_CODE_SYSTEM_PROMPT,
            },
            {"role": "user", "content": prompt},
        ]
        temperature = kwargs.get("temperature", 0.1)
        response_format = kwargs.get("response_format") or {
            "type": "json_schema",
            "json_schema": {
                "name": "analysis_response",
                "schema": DEFAULT_CODE_RESPONSE_SCHEMA,
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_body = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": temperature,
                "response_format": response_format,
            }
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
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code == 400
                    and response_format.get("type") == "json_schema"
                ):
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
                else:
                    raise
            payload = response.json()

        content = payload["choices"][0]["message"]["content"]
        return {
            "raw": payload,
            "code": content,
            "usage": payload.get("usage", {}),
        }

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        await self.ensure_credentials()
        temperature = kwargs.get("temperature", 0.3)
        body: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": temperature,
        }
        if "response_format" in kwargs:
            body["response_format"] = kwargs["response_format"]

        async with httpx.AsyncClient(timeout=40.0) as client:
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

        message = payload["choices"][0]["message"]
        return {"raw": payload, "message": message, "usage": payload.get("usage", {})}

    async def list_models(self) -> list[str]:
        try:
            await self.ensure_credentials()
        except RuntimeError:
            return self.default_models
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
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
                return models or self.default_models
        except Exception:
            return self.default_models
