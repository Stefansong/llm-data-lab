import { readAccessToken, writeAccessToken } from "@/lib/authToken";
import { clearActiveUserId, readActiveUserId } from "@/lib/userProfile";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TaskType = "strategy" | "analysis";
export type TaskStatus = "queued" | "running" | "succeeded" | "failed";

export interface LLMGeneratePayload {
  prompt: string;
  model: string;
  taskType?: TaskType;
  datasetContext?: string;
  providerOverrides?: ProviderOverrideMap;
}

export interface LLMGenerateResponse {
  code: string;
  model: string;
  prompt: string;
  reasoning?: string | null;
  usage?: Record<string, unknown> | null;
}

export interface ProviderOverridePayload {
  apiKey?: string;
  baseUrl?: string;
  defaultModels?: string[];
}

export type ProviderOverrideMap = Record<string, ProviderOverridePayload>;

export interface CodeExecutionPayload {
  code: string;
  taskId?: number;
  datasetFilename?: string;
}

export interface ArtifactInfo {
  filename: string;
  url: string;
  mimetype?: string | null;
}

export interface CodeExecutionResult {
  stdout: string;
  stderr?: string | null;
  status: TaskStatus;
  artifacts: ArtifactInfo[];
  celeryTaskId?: string | null;
}

export interface DatasetUploadResponse {
  filename: string;
  original_filename: string;
  columns: string[];
  schema: Record<string, string>;
  preview: Record<string, unknown>[];
  rows: number;
}

export interface AnalysisTask {
  id: number;
  user_id: number;
  title: string;
  prompt: string;
  model: string;
  generated_code?: string | null;
  execution_stdout?: string | null;
  execution_stderr?: string | null;
  status: TaskStatus;
  summary?: string | null;
  dataset_filename?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskPayload {
  title: string;
  prompt: string;
  model: string;
  generated_code?: string | null;
  dataset_filename?: string | null;
  status?: TaskStatus;
}

export interface UserInfo {
  id: number;
  username: string;
  email?: string | null;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}


export interface LLMProviderInfo {
  id: string;
  name: string;
  models: string[];
}

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessagePayload {
  role: ChatRole;
  content: string;
}

export interface ChatContext {
  code_snapshot?: string | null;
  stdout?: string | null;
  stderr?: string | null;
}

export interface ChatSendRequest {
  model: string;
  sessionId?: number;
  taskId?: number;
  messages: ChatMessagePayload[];
  context?: ChatContext;
  providerOverrides?: ProviderOverrideMap;
}

export interface ChatMessageResponse {
  session_id: number;
  message: ChatMessagePayload;
  reasoning?: string | null;
  patch?: string | null;
  usage?: Record<string, unknown> | null;
}

export interface ChatSessionSummary {
  id: number;
  user_id: number;
  task_id?: number | null;
  model: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageRecord {
  role: ChatRole;
  content: string;
  patch?: string | null;
  reasoning?: string | null;
  usage?: Record<string, unknown> | null;
  created_at: string;
}

export interface ChatSessionHistory {
  session: ChatSessionSummary;
  messages: ChatMessageRecord[];
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("X-User-Id", String(readActiveUserId()));
  const token = readAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (response.status === 401) {
    writeAccessToken(null);
    clearActiveUserId();
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

function serializeProviderOverrides(overrides?: ProviderOverrideMap) {
  if (!overrides) {
    return undefined;
  }
  const entries = Object.entries(overrides)
    .map(([providerId, value]) => {
      if (!value) {
        return null;
      }
      const payload: Record<string, unknown> = {};
      if (value.apiKey) {
        payload.api_key = value.apiKey;
      }
      if (value.baseUrl) {
        payload.base_url = value.baseUrl;
      }
      if (value.defaultModels && value.defaultModels.length > 0) {
        payload.default_models = value.defaultModels;
      }
      if (Object.keys(payload).length === 0) {
        return null;
      }
      return [providerId, payload] as const;
    })
    .filter((entry): entry is readonly [string, Record<string, unknown>] => Boolean(entry));

  if (!entries.length) {
    return undefined;
  }

  return Object.fromEntries(entries);
}

export function generateCode(payload: LLMGeneratePayload) {
  return request<LLMGenerateResponse>("/llm/generate", {
    method: "POST",
    body: JSON.stringify({
      prompt: payload.prompt,
      model: payload.model,
      task_type: payload.taskType ?? "analysis",
      dataset_context: payload.datasetContext,
      provider_overrides: serializeProviderOverrides(payload.providerOverrides),
    }),
  });
}

export function executeCode(payload: CodeExecutionPayload) {
  return request<CodeExecutionResult>("/analysis/run", {
    method: "POST",
    body: JSON.stringify({
      code: payload.code,
      task_id: payload.taskId,
      dataset_filename: payload.datasetFilename,
    }),
  });
}

export async function uploadDataset(file: File): Promise<DatasetUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const headers = new Headers();
  headers.set("X-User-Id", String(readActiveUserId()));
  const token = readAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
    method: "POST",
    body: formData,
    headers,
  });
  if (response.status === 401) {
    writeAccessToken(null);
    clearActiveUserId();
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Upload failed with status ${response.status}`);
  }
  return (await response.json()) as DatasetUploadResponse;
}

export function listHistory(limit = 20) {
  return request<AnalysisTask[]>(`/history/tasks?limit=${limit}`, {
    method: "GET",
  });
}

export function createTask(payload: CreateTaskPayload) {
  return request<AnalysisTask>("/history/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: payload.title,
      prompt: payload.prompt,
      model: payload.model,
      generated_code: payload.generated_code,
      dataset_filename: payload.dataset_filename,
      status: payload.status ?? "queued",
    }),
  });
}

export function getTask(taskId: number) {
  return request<AnalysisTask>(`/history/tasks/${taskId}`, {
    method: "GET",
  });
}

export function sendChat(payload: ChatSendRequest) {
  return request<ChatMessageResponse>("/chat/send", {
    method: "POST",
    body: JSON.stringify({
      model: payload.model,
      session_id: payload.sessionId,
      task_id: payload.taskId,
      messages: payload.messages,
      context: payload.context,
      provider_overrides: serializeProviderOverrides(payload.providerOverrides),
    }),
  });
}

export function listChatSessions(taskId?: number) {
  const search = taskId ? `?task_id=${taskId}` : "";
  return request<ChatSessionSummary[]>(`/chat/sessions${search}`, {
    method: "GET",
  });
}

export function getChatSession(sessionId: number) {
  return request<ChatSessionHistory>(`/chat/sessions/${sessionId}`, {
    method: "GET",
  });
}

export function listProviders() {
  return request<LLMProviderInfo[]>("/llm/providers", {
    method: "GET",
  });
}

export function getProviderCredentials() {
  return request<ProviderOverrideMap>("/providers/credentials", {
    method: "GET",
  });
}

export function updateProviderCredentials(map: ProviderOverrideMap) {
  return request<ProviderOverrideMap>("/providers/credentials", {
    method: "PUT",
    body: JSON.stringify(map),
  });
}

export function registerUser(payload: RegisterPayload) {
  return request<AuthTokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload: LoginPayload) {
  return request<AuthTokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCurrentUser() {
  return request<UserInfo>("/auth/me", {
    method: "GET",
  });
}
