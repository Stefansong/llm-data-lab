from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


TaskStatus = Literal["queued", "running", "succeeded", "failed"]
ChatRole = Literal["user", "assistant", "system"]


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    email: Optional[EmailStr] = None


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    created_at: datetime

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ProviderCredentialPayload(BaseModel):
    apiKey: Optional[str] = None
    baseUrl: Optional[str] = None
    defaultModels: Optional[list[str]] = None


class ProviderOverride(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_models: Optional[list[str]] = None


class LLMGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language task description from user.")
    model: str = Field(..., description="LLM provider identifier.")
    task_type: Literal["strategy", "analysis"] = "analysis"
    dataset_context: Optional[str] = Field(
        default=None,
        description="Optional context or schema extracted from uploaded dataset to guide code generation.",
    )
    provider_overrides: Optional[Dict[str, ProviderOverride]] = None


class LLMGenerateResponse(BaseModel):
    code: str
    model: str
    prompt: str
    reasoning: Optional[str] = None
    usage: Optional[dict] = None


class CodeExecutionRequest(BaseModel):
    code: str
    task_id: Optional[int] = None
    dataset_filename: Optional[str] = None


class ArtifactInfo(BaseModel):
    filename: str
    url: str
    mimetype: Optional[str] = None


class CodeExecutionResult(BaseModel):
    stdout: str
    stderr: Optional[str] = None
    status: TaskStatus
    artifacts: list[ArtifactInfo] = Field(default_factory=list)


class AnalysisTaskCreate(BaseModel):
    title: str
    prompt: str
    model: str
    generated_code: Optional[str] = None
    dataset_filename: Optional[str] = None
    status: TaskStatus = "queued"




class LLMProviderInfo(BaseModel):
    id: str
    name: str
    models: list[str]

class AnalysisTaskRead(BaseModel):
    id: int
    user_id: int
    title: str
    prompt: str
    model: str
    generated_code: Optional[str] = None
    execution_stdout: Optional[str] = None
    execution_stderr: Optional[str] = None
    status: TaskStatus
    summary: Optional[str] = None
    dataset_filename: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessagePayload(BaseModel):
    role: ChatRole
    content: str


class ChatTurnMetadata(BaseModel):
    code_snapshot: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ChatSendRequest(BaseModel):
    model: str
    messages: list[ChatMessagePayload]
    session_id: Optional[int] = None
    task_id: Optional[int] = None
    context: Optional[ChatTurnMetadata] = None
    provider_overrides: Optional[Dict[str, ProviderOverride]] = None


class ChatMessageResponse(BaseModel):
    session_id: int
    message: ChatMessagePayload
    reasoning: Optional[str] = None
    patch: Optional[str] = None
    usage: Optional[dict] = None


class ChatSessionRead(BaseModel):
    id: int
    user_id: int
    task_id: Optional[int] = None
    model: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageRecord(BaseModel):
    role: ChatRole
    content: str
    patch: Optional[str] = None
    reasoning: Optional[str] = None
    usage: Optional[dict] = None
    created_at: datetime


class ChatSessionHistoryResponse(BaseModel):
    session: ChatSessionRead
    messages: list[ChatMessageRecord]
