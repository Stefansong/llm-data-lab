import json
import re
import ast
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException

from ..api.dependencies import get_current_user_id, get_database
from ..llm_adapters.factory import adapter_factory
from ..schemas import LLMGenerateRequest, LLMGenerateResponse, LLMProviderInfo
from ..services import provider_credentials_service
from ..config import get_settings
from ..services.prompt_builder import build_analysis_prompt

router = APIRouter(prefix="/llm", tags=["llm"])


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    lines = stripped.splitlines()
    if not lines:
        return text
    lines = lines[1:]  # drop opening fence (with optional language)
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _normalize_code(text: str) -> str:
    # If the provider returned escaped newlines, collapse them into real ones.
    if "\n" not in text and "\\n" in text:
        return text.replace("\\r\\n", "\n").replace("\\n", "\n")
    return text


def _extract_code_from_payload(payload: Dict[str, Any]) -> Tuple[str, str | None]:
    candidates = [
        (payload.get("code"), payload.get("reasoning")),
        (payload.get("output", {}).get("code"), payload.get("output", {}).get("reasoning")),
        (
            payload.get("result", {}).get("code"),
            payload.get("result", {}).get("reasoning"),
        ),
    ]
    for code, reasoning in candidates:
        if isinstance(code, str) and code.strip():
            return _normalize_code(code), reasoning if isinstance(reasoning, str) else None
    return "", None


def _extract_from_json_like(raw_text: str) -> Tuple[str, str | None]:
    code_match = re.search(r'"code"\s*:\s*"', raw_text)
    if not code_match:
        return "", None
    idx = code_match.end()
    buffer: list[str] = []
    escaped = False
    while idx < len(raw_text):
        ch = raw_text[idx]
        if escaped:
            buffer.append(ch)
            escaped = False
        elif ch == "\\":
            buffer.append(ch)
            escaped = True
        elif ch == '"':
            break
        else:
            buffer.append(ch)
        idx += 1
    code_literal = "".join(buffer)
    try:
        code_str = json.loads(f'"{code_literal}"')
    except json.JSONDecodeError:
        code_str = code_literal.replace("\\r\\n", "\n").replace("\\n", "\n")
    return _normalize_code(code_str), None


def _extract_code_and_reasoning(raw_text: str) -> Tuple[str, str | None]:
    """Extract Python code from mixed content responses."""
    cleaned = _strip_code_fence(raw_text)
    parse_attempts = []
    try:
        parse_attempts.append(json.loads(cleaned))
    except json.JSONDecodeError:
        try:
            parse_attempts.append(ast.literal_eval(cleaned))
        except (ValueError, SyntaxError):
            pass

    for payload in parse_attempts:
        if isinstance(payload, dict):
            code, reasoning = _extract_code_from_payload(payload)
            if code:
                return code, reasoning

    code, reasoning = _extract_from_json_like(cleaned)
    if code:
        return code, reasoning

    pattern = re.compile(r"```python\n(?P<code>.*?)```", re.DOTALL)
    match = pattern.search(raw_text)
    if match:
        return _normalize_code(match.group("code").strip()), None
    return _normalize_code(raw_text.strip()), None




@router.get("/providers", response_model=list[LLMProviderInfo])
async def list_providers(
    db=Depends(get_database), user_id: int = Depends(get_current_user_id)
) -> list[LLMProviderInfo]:
    stored = await provider_credentials_service.get_credentials_map(db, user_id)
    overrides = provider_credentials_service.credential_payloads_to_overrides(stored)
    providers = await adapter_factory.list_all(overrides)
    return [LLMProviderInfo(**provider) for provider in providers]


@router.post("/generate", response_model=LLMGenerateResponse)
async def generate_code(
    payload: LLMGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_database),
) -> LLMGenerateResponse:
    prompt = build_analysis_prompt(
        task_description=payload.prompt,
        task_type=payload.task_type,
        dataset_context=payload.dataset_context,
    )
    provider, _, variant = payload.model.partition(":")
    stored_map = await provider_credentials_service.get_credentials_map(db, user_id)
    stored_overrides = provider_credentials_service.credential_payloads_to_overrides(stored_map)
    request_override = (payload.provider_overrides or {}).get(provider)
    override = provider_credentials_service.merge_overrides(
        stored_overrides.get(provider), request_override
    )
    try:
        adapter = adapter_factory.get(provider, override=override)
        # Force backend default for OpenAI when user selected "Default Model" (no variant)
        forced_kwargs: Dict[str, Any] = {}
        effective_model_str = payload.model
        if provider == "openai" and not variant:
            settings = get_settings()
            forced_model = (settings.openai_default_models[0] if settings.openai_default_models else "gpt-4o")
            forced_kwargs["model"] = forced_model
            effective_model_str = f"openai:{forced_model}"
        elif variant:
            forced_kwargs["model"] = variant
            effective_model_str = payload.model
        result = await adapter.generate_code(prompt, **forced_kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream API failures
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    code, reasoning = _extract_code_and_reasoning(result.get("code", ""))
    return LLMGenerateResponse(
        code=code,
        model=effective_model_str,
        prompt=payload.prompt,
        reasoning=reasoning,
        usage=result.get("usage"),
    )
