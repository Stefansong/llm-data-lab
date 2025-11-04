import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..api.dependencies import get_current_user_id, get_database
from ..llm_adapters.factory import adapter_factory
from ..schemas import (
    ChatMessagePayload,
    ChatMessageRecord,
    ChatMessageResponse,
    ChatSendRequest,
    ChatSessionHistoryResponse,
    ChatSessionRead,
)
from ..services import chat_service, provider_credentials_service
from ..config import get_settings
import difflib

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_INSTRUCTIONS = """
You are an AI pair programmer assisting with scientific Python analytics code.
Always respond as a JSON object with the following fields:
  - "reply": natural language guidance for the user.
  - "patch": either null or a unified diff (starting with diff/@@ lines) describing code changes against the current notebook. Only include a diff when modifications are required and never return raw code outside of a diff.
  - "reasoning": optional brief rationale of your changes.
Do not include any additional keys. Escape newline characters with actual newlines inside the JSON string values.
When replying, use the same language as the latest user message unless explicitly instructed otherwise.
""".strip()


def _serialize_message(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content)
    return str(content)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove optional language hint, keep inner payload.
        fence_split = stripped.split("\n", 1)
        if len(fence_split) == 2:
            payload = fence_split[1]
        else:
            payload = ""
        if payload.endswith("```"):
            payload = payload[: -3]
        return payload.strip()
    return text


def _parse_structured_response(message: Dict[str, Any]) -> Dict[str, Optional[str]]:
    raw_text = _serialize_message(message)
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "reply" in data:
            return {
                "reply": data.get("reply", ""),
                "patch": data.get("patch"),
                "reasoning": data.get("reasoning"),
            }
    except json.JSONDecodeError:
        pass
    diff_match = re.search(r"```(?:diff|patch)\s*(?P<diff>.*?)```", raw_text, re.DOTALL)
    if diff_match:
        diff_block = diff_match.group("diff").strip()
        reply_text = (
            raw_text[: diff_match.start()] + raw_text[diff_match.end() :]
        ).strip()
        diff_block = _strip_code_fence(diff_block)
        if not diff_block.startswith("diff"):
            diff_block = "diff --git a/current_script.py b/current_script.py\n" + diff_block
        return {"reply": reply_text, "patch": diff_block, "reasoning": None}
    # Fallback: return raw text as reply
    return {"reply": raw_text, "patch": None, "reasoning": None}


def _is_diff_patch(text: Optional[str]) -> bool:
    if not text or not isinstance(text, str):
        return False
    t = text.lstrip()
    return t.startswith("diff ") or t.startswith("@@") or t.startswith("--- ") or t.startswith("+++") or "\n@@" in t


def _build_unified_diff(old: str, new: str, *, fromfile: str = "a/analysis.py", tofile: str = "b/analysis.py") -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff_iter = difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm="")
    return "\n".join(diff_iter)


def _detect_lang(text: str) -> str:
    """Detect rough language preference from last user message.
    Returns "zh" if contains CJK ideographs, otherwise "en".
    """
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


def _try_build_patch_from_json_patches(raw_text: str, base_code: Optional[str]) -> Optional[str]:
    """Support models that return RFC6902-like patches: {"patches":[{"op":"replace","path":"/83","value":"..."}]}.
    Only implements simple line-level replace for now.
    """
    if base_code is None:
        return None
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    patches = data.get("patches") if isinstance(data, dict) else None
    if not isinstance(patches, list) or not patches:
        return None

    base_lines = base_code.splitlines()
    new_lines = base_lines[:]
    # Apply only simple replace ops with path '/<line>' (1-based)
    ops: list[tuple[int, str]] = []
    for item in patches:
        if not isinstance(item, dict):
            continue
        if item.get("op") != "replace":
            continue
        path = item.get("path", "")
        if not isinstance(path, str) or not path.startswith("/"):
            continue
        try:
            line_no = int(path.lstrip("/"))
        except ValueError:
            continue
        value = item.get("value")
        if not isinstance(value, str):
            continue
        # Treat as 1-based index; clamp into range
        idx = max(1, min(line_no, len(new_lines))) - 1
        ops.append((idx, value))

    if not ops:
        return None
    for idx, value in ops:
        new_lines[idx] = value

    diff_iter = difflib.unified_diff(
        base_lines,
        new_lines,
        fromfile="a/current_script.py",
        tofile="b/current_script.py",
        lineterm="",
    )
    patch_text = "\n".join(diff_iter)
    return patch_text if patch_text.strip() else None


def _augment_user_content(message: ChatMessagePayload, context: Optional[dict]) -> str:
    content = message.content
    if context:
        fragments: List[str] = [content, "\n\n--- Context Snapshot ---"]
        if context.get("code_snapshot"):
            fragments.append("Current code:\n" + context["code_snapshot"])
        if context.get("stdout"):
            fragments.append("Last stdout:\n" + context["stdout"])
        if context.get("stderr"):
            fragments.append("Last stderr:\n" + context["stderr"])
        content = "\n\n".join(fragments)
    return content


@router.post("/send", response_model=ChatMessageResponse)
async def send_chat(
    payload: ChatSendRequest,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> ChatMessageResponse:
    provider, _, variant = payload.model.partition(":")
    stored_map = await provider_credentials_service.get_credentials_map(db, user_id)
    stored_overrides = provider_credentials_service.credential_payloads_to_overrides(stored_map)
    request_override = (payload.provider_overrides or {}).get(provider)
    override = provider_credentials_service.merge_overrides(
        stored_overrides.get(provider), request_override
    )
    try:
        adapter = adapter_factory.get(provider, override=override)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Compute the effective model string for record-keeping
    effective_model_str = payload.model
    if provider == "openai" and not variant:
        settings = get_settings()
        forced = settings.openai_default_models[0] if settings.openai_default_models else "gpt-4o"
        effective_model_str = f"openai:{forced}"

    session_id = await chat_service.ensure_session(
        db,
        session_id=payload.session_id,
        task_id=payload.task_id,
        model=effective_model_str,
        user_id=user_id,
    )

    # Persist incoming user message (assume last message is most recent user turn)
    if not payload.messages:
        raise HTTPException(status_code=400, detail="Chat messages cannot be empty.")

    latest = payload.messages[-1]
    if latest.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user.")

    context_payload = payload.context.model_dump() if payload.context else None
    await chat_service.append_message(
        db,
        session_id=session_id,
        role="user",
        content=latest.content,
        metadata=context_payload,
    )

    system_message = {"role": "system", "content": SYSTEM_INSTRUCTIONS}
    serialized_messages: List[Dict[str, str]] = [system_message]
    for message in payload.messages:
        if message.role == "user":
            content = _augment_user_content(message, context_payload)
        else:
            content = message.content
        serialized_messages.append({"role": message.role, "content": content})

    generated_code = None
    if payload.task_id:
        latest_task = await chat_service.get_latest_task_code(db, payload.task_id, user_id)
        if latest_task:
            generated_code = latest_task

    if generated_code:
        serialized_messages.append(
            {
                "role": "system",
                "content": (
                    "Here is the current Python script that the user is working with."
                    " When responding, reference and modify this code only via diff patches.\n\n"
                    f"```python\n{generated_code}\n```"
                ),
            }
        )

    # Language steering based on the last user message
    user_lang = _detect_lang(latest.content)
    if user_lang == "zh":
        serialized_messages.append(
            {
                "role": "system",
                "content": (
                    "For this turn, reply strictly in Simplified Chinese (zh-CN). "
                    "All fields in the JSON ('reply' and 'reasoning') must be Chinese."
                ),
            }
        )
    else:
        serialized_messages.append(
            {
                "role": "system",
                "content": (
                    "For this turn, reply strictly in English. "
                    "All fields in the JSON ('reply' and 'reasoning') must be English."
                ),
            }
        )

    try:
        # When using Default Model for OpenAI, force backend default (e.g., GPT-4o)
        model_param: Optional[str] = variant or None
        if provider == "openai" and not variant:
            settings = get_settings()
            model_param = settings.openai_default_models[0] if settings.openai_default_models else "gpt-4o"
        result = await adapter.chat(
            serialized_messages,
            model=model_param,
            response_format={"type": "json_object"},
        )
    except NotImplementedError:
        raise HTTPException(status_code=400, detail="Selected model does not support chat.")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    message_payload = result.get("message", {})
    structured = _parse_structured_response(message_payload)
    # Try to ensure patch is unified diff. Prefer provider-provided patch; otherwise convert.
    base_code = (context_payload.get("code_snapshot") if context_payload else None) or generated_code
    if base_code:
        # Case 1: structured.patch exists but isn't a diff; interpret as full new code and diff it.
        if structured.get("patch") and not _is_diff_patch(structured.get("patch")):
            candidate_new = _strip_code_fence(structured["patch"] or "")
            if candidate_new.strip():
                patch_text = _build_unified_diff(base_code, candidate_new)
                if patch_text.strip():
                    structured["patch"] = patch_text
        # Case 2: No patch at all – try RFC6902-like patches on top of current code.
        if structured.get("patch") is None:
            maybe_patch = _try_build_patch_from_json_patches(_serialize_message(message_payload), base_code)
            if maybe_patch:
                structured["patch"] = maybe_patch

    await chat_service.append_message(
        db,
        session_id=session_id,
        role="assistant",
        content=structured["reply"] or "",
        metadata={
            "patch": structured.get("patch"),
            "reasoning": structured.get("reasoning"),
            "usage": result.get("usage"),
        },
    )

    return ChatMessageResponse(
        session_id=session_id,
        message=ChatMessagePayload(role="assistant", content=structured["reply"] or ""),
        reasoning=structured.get("reasoning"),
        patch=structured.get("patch"),
        usage=result.get("usage"),
    )


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_chat_sessions(
    task_id: Optional[int] = None,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> list[ChatSessionRead]:
    rows = await chat_service.list_sessions(db, user_id=user_id, task_id=task_id)
    return [
        ChatSessionRead(
            id=row["id"],
            user_id=row["user_id"],
            task_id=row["task_id"],
            model=row["model"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionHistoryResponse)
async def get_chat_session(
    session_id: int,
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> ChatSessionHistoryResponse:
    session = await chat_service.get_session(db, session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = await chat_service.get_session_messages(db, session_id)
    records: list[ChatMessageRecord] = []
    for item in messages:
        metadata = item.get("metadata") or {}
        if item["role"] == "system":
            continue
        records.append(
            ChatMessageRecord(
                role=item["role"],
                content=item["content"],
                patch=metadata.get("patch"),
                reasoning=metadata.get("reasoning"),
                usage=metadata.get("usage"),
                created_at=item["created_at"],
            )
        )

    return ChatSessionHistoryResponse(
        session=ChatSessionRead(
            id=session["id"],
            user_id=session["user_id"],
            task_id=session["task_id"],
            model=session["model"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        ),
        messages=records,
    )
