from __future__ import annotations

from time import monotonic
from typing import Callable, Dict, List, Optional, Tuple

from ..config import get_settings
from ..schemas import ProviderOverride
from .anthropic_adapter import AnthropicAdapter
from .base import LLMAdapter
from .deepseek_adapter import DeepSeekAdapter
from .openai_adapter import OpenAIAdapter
from .qwen_adapter import QwenAdapter
from .siliconflow_adapter import SiliconFlowAdapter


def _select_models(
    override_models: Optional[list[str]],
    configured_models: Optional[list[str]],
    fallback: list[str],
) -> list[str]:
    models = override_models or configured_models or fallback
    return list(models)


class AdapterFactory:
    """Factory that instantiates adapters and exposes provider metadata."""

    def __init__(self) -> None:
        settings = get_settings()
        self._registry: Dict[str, Dict[str, object]] = {}

        def register(
            key: str,
            display_name: str,
            factory: Callable[[Optional[ProviderOverride]], LLMAdapter],
        ) -> None:
            adapter = factory(None)
            self._registry[key] = {
                "display_name": display_name,
                "factory": factory,
                "adapter": adapter,
            }

        register(
            "openai",
            "OpenAI",
            lambda override: OpenAIAdapter(
                api_key=(override.api_key if override and override.api_key else settings.openai_api_key),
                model=_select_models(
                    override.default_models if override else None,
                    settings.openai_default_models,
                    ["gpt-4o-mini"],
                )[0],
                default_models=_select_models(
                    override.default_models if override else None,
                    settings.openai_default_models,
                    ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
                ),
            ),
        )

        register(
            "anthropic",
            "Anthropic",
            lambda override: AnthropicAdapter(
                api_key=(override.api_key if override and override.api_key else settings.anthropic_api_key),
                model=_select_models(
                    override.default_models if override else None,
                    ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                    ["claude-3-sonnet-20240229"],
                )[0],
                default_models=_select_models(
                    override.default_models if override else None,
                    ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                    ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                ),
            ),
        )


        register(
            "deepseek",
            "DeepSeek",
            lambda override: DeepSeekAdapter(
                api_key=(override.api_key if override and override.api_key else settings.deepseek_api_key),
                base_url=(override.base_url if override and override.base_url else settings.deepseek_base_url),
                default_models=_select_models(
                    override.default_models if override else None,
                    settings.deepseek_default_models,
                    ["deepseek-chat", "deepseek-coder"],
                ),
            ),
        )

        register(
            "qwen",
            "Qwen (DashScope)",
            lambda override: QwenAdapter(
                api_key=(override.api_key if override and override.api_key else settings.dashscope_api_key),
                base_url=(override.base_url if override and override.base_url else settings.dashscope_base_url),
                default_models=_select_models(
                    override.default_models if override else None,
                    settings.qwen_default_models,
                    ["qwen-turbo", "qwen-plus", "qwen-max"],
                ),
            ),
        )

        register(
            "siliconflow",
            "SiliconFlow",
            lambda override: SiliconFlowAdapter(
                api_key=(override.api_key if override and override.api_key else settings.siliconflow_api_key),
                base_url=(override.base_url if override and override.base_url else settings.siliconflow_base_url),
                default_models=_select_models(
                    override.default_models if override else None,
                    settings.siliconflow_default_models,
                    ["siliconflow-chat", "siliconflow-coder"],
                ),
            ),
        )

        self._model_cache: Dict[str, Tuple[float, List[str]]] = {}
        self._cache_ttl_seconds = 120.0

    def _get_cached_models(self, name: str) -> List[str] | None:
        cached = self._model_cache.get(name)
        if not cached:
            return None
        timestamp, models = cached
        if monotonic() - timestamp < self._cache_ttl_seconds:
            return models
        return None

    def _dedupe(self, models: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for item in models:
            if item and item not in seen:
                ordered.append(item)
                seen.add(item)
        return ordered

    async def _resolve_models(self, name: str, override: Optional[ProviderOverride] = None) -> List[str]:
        if override is None:
            cached = self._get_cached_models(name)
            if cached is not None:
                return cached

        adapter = self.get(name, override=override)
        try:
            models = await adapter.list_models()
        except Exception:
            models = adapter.default_models

        deduped = self._dedupe(models)
        if override is None:
            self._model_cache[name] = (monotonic(), deduped)
        return deduped

    def clear_cache(self) -> None:
        self._model_cache.clear()

    def get(self, name: str, override: Optional[ProviderOverride] = None) -> LLMAdapter:
        normalized = name.lower()
        entry = self._registry.get(normalized)
        if not entry:
            raise KeyError(f"Unsupported LLM provider: {name}")
        if override:
            factory: Callable[[Optional[ProviderOverride]], LLMAdapter] = entry["factory"]  # type: ignore[assignment]
            return factory(override)
        return entry["adapter"]  # type: ignore[return-value]

    def providers(self) -> Dict[str, Dict[str, object]]:
        return self._registry

    def get_display_name(self, name: str) -> str:
        normalized = name.lower()
        entry = self._registry.get(normalized)
        if not entry:
            raise KeyError(f"Unsupported LLM provider: {name}")
        return entry.get("display_name", name.title())  # type: ignore[return-value]

    async def list_models(self, name: str, override: Optional[ProviderOverride] = None) -> List[str]:
        return await self._resolve_models(name, override=override)

    async def list_all(
        self, overrides: Optional[Dict[str, ProviderOverride]] = None
    ) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        for key, entry in self._registry.items():
            override = overrides.get(key) if overrides else None
            models = await self._resolve_models(key, override=override)
            results.append(
                {
                    "id": key,
                    "name": entry.get("display_name", key.title()),
                    "models": models,
                }
            )
        return results


adapter_factory = AdapterFactory()
