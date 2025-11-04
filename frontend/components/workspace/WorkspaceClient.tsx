"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { applyPatch as applyTextPatch, createTwoFilesPatch } from "diff";
import { Eye, EyeOff } from "lucide-react";

import {
  API_BASE_URL,
  CodeExecutionPayload,
  CodeExecutionResult,
  DatasetUploadResponse,
  TaskType,
  generateCode,
  createTask,
  executeCode,
  uploadDataset,
  sendChat,
  ChatMessagePayload,
  listChatSessions,
  getChatSession,
  listProviders,
  LLMProviderInfo,
} from "@/lib/api";
import { Alert } from "@/components/ui/Alert";
import { LANG_UPDATED_EVENT, readLang, workspaceTexts, type Lang } from "@/lib/i18n";
import { ChatPanel, WorkspaceChatMessage } from "@/components/workspace/ChatPanel";
import {
  PROVIDER_CREDENTIALS_UPDATED_EVENT,
  ProviderCredentialMap,
  fetchProviderCredentials,
} from "@/lib/providerSettings";
import { subscribeToUserIdChange } from "@/lib/userProfile";
// 个人偏好已移除

function extractSnippetsFromDiff(patch: string): string[] {
  const lines = patch.split("\n");
  const snippets: string[] = [];
  let current: string[] | null = null;
  let headerSig: string | null = null;

  const flush = () => {
    if (!current || current.length === 0) return;
    let body = current.join("\n");
    const needsHeader = headerSig && !/^\s*(async\s+)?def\s+|^\s*class\s+/.test(body);
    if (needsHeader) {
      // Inject the header signature as a def/class line to help function-level merge.
      // Example: '@@ -8,6 +8,10 @@ def load_data(path):' -> 'def load_data(path):\n<body>'
      const sig = headerSig!.trim();
      const normalizedSig = sig.replace(/^@@.*?@@\s*/, "");
      // Only inject if signature looks like def/class
      if (/^(async\s+)?def\s+|^class\s+/.test(normalizedSig)) {
        body = `${normalizedSig}\n${body}`;
      }
    }
    snippets.push(body);
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("@@")) {
      if (current && current.length > 0) {
        flush();
      }
      current = [];
      // capture signature after the second '@@'
      const secondIdx = line.indexOf("@@", 2);
      headerSig = secondIdx !== -1 ? line.slice(secondIdx + 2).trim() : line.replace(/^@@+\s*/, "").trim();
      continue;
    }

    if (current === null) {
      continue;
    }

    if (line.startsWith("+++")) continue;
    if (line.startsWith("---")) continue;
    if (line.startsWith("+")) {
      current.push(line.slice(1));
      continue;
    }
    if (line.startsWith(" ")) {
      current.push(line.slice(1));
      continue;
    }
    // Removed lines ('-') are ignored for snippet reconstruction
  }

  if (current && current.length > 0) {
    flush();
  }

  return snippets.filter((snippet) => snippet.trim().length > 0);
}

function isDiffPatch(patch: string): boolean {
  const trimmed = patch.trimStart();
  return (
    trimmed.startsWith("diff") ||
    trimmed.startsWith("@@") ||
    trimmed.startsWith("--- ") ||
    trimmed.startsWith("+++") ||
    trimmed.includes("\n@@")
  );
}

function mergeMultipleSnippets(existing: string, snippets: string[]): string | null {
  let current = existing;
  let applied = false;
  for (const snippet of snippets) {
    const merged = mergeFunctionOrClassSnippet(current, snippet);
    if (merged) {
      current = merged;
      applied = true;
    }
  }
  return applied ? current : null;
}

function mergeFunctionOrClassSnippet(existing: string, snippet: string): string | null {
  const normalize = (text: string) => text.replace(/\r\n/g, "\n");
  const existingCode = normalize(existing);
  const snippetNormalized = normalize(snippet).trimEnd();
  const rawLines = snippetNormalized.split("\n");

  let firstContentIdx = rawLines.findIndex((line) => line.trim() !== "");
  if (firstContentIdx === -1) {
    return null;
  }

  let defLineIdx = -1;
  for (let i = firstContentIdx; i < rawLines.length; i += 1) {
    const trimmed = rawLines[i].trim();
    if (/^(async\s+)?def\s+[A-Za-z0-9_]+\s*\(/.test(trimmed) || /^class\s+[A-Za-z0-9_]+\s*:/.test(trimmed)) {
      defLineIdx = i;
      break;
    }
  }
  if (defLineIdx === -1) {
    return null;
  }

  let snippetStart = defLineIdx;
  while (snippetStart > 0 && rawLines[snippetStart - 1].trim().startsWith("@")) {
    snippetStart -= 1;
  }
  const snippetLines = rawLines.slice(snippetStart);
  const defLine = snippetLines.find((line) => line.trim().length > 0) ?? "";
  const defMatch =
    defLine.trim().match(/^(async\s+)?def\s+([A-Za-z0-9_]+)/) ||
    defLine.trim().match(/^class\s+([A-Za-z0-9_]+)/);
  if (!defMatch) {
    return null;
  }

  const name = defMatch[defMatch.length - 1];
  const isClass = defLine.trim().startsWith("class ");
  const existingLines = existingCode.split("\n");

  let matchIndex = existingLines.findIndex((line) => {
    const trimmed = line.trim();
    if (isClass) {
      return trimmed.startsWith(`class ${name}`);
    }
    return /^(async\s+)?def\s+/.test(trimmed) && trimmed.startsWith(`def ${name}`) || trimmed.startsWith(`async def ${name}`);
  });
  if (matchIndex === -1) {
    return null;
  }

  let replaceStart = matchIndex;
  while (replaceStart > 0 && existingLines[replaceStart - 1].trim().startsWith("@")) {
    replaceStart -= 1;
  }

  const baseIndentMatch = existingLines[matchIndex].match(/^\s*/);
  const baseIndent = baseIndentMatch ? baseIndentMatch[0] : "";
  let replaceEnd = matchIndex + 1;
  while (replaceEnd < existingLines.length) {
    const line = existingLines[replaceEnd];
    const trimmed = line.trim();
    if (!trimmed) {
      replaceEnd += 1;
      continue;
    }
    const indentMatch = line.match(/^\s*/);
    const indent = indentMatch ? indentMatch[0] : "";
    if (indent.length <= baseIndent.length && !trimmed.startsWith("#")) {
      break;
    }
    replaceEnd += 1;
  }

  const before = existingLines.slice(0, replaceStart);
  const after = existingLines.slice(replaceEnd);
  const mergedLines = [...before, ...snippetLines, ...after];
  return mergedLines.join("\n");
}

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

const FALLBACK_PROVIDERS: LLMProviderInfo[] = [
  {
    id: "openai",
    name: "OpenAI",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    models: ["deepseek-chat", "deepseek-coder"],
  },
  {
    id: "qwen",
    name: "Qwen",
    models: ["qwen-turbo", "qwen-plus", "qwen-max"],
  },
  {
    id: "siliconflow",
    name: "SiliconFlow",
    models: ["siliconflow-chat", "siliconflow-coder"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    models: ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    models: ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
  },
];

const taskTypes: { label: string; value: TaskType }[] = [
  { label: "分析策略", value: "strategy" },
  { label: "数据分析", value: "analysis" },
];

export function WorkspaceClient() {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const L = useMemo(() => workspaceTexts[lang], [lang]);
  const [prompt, setPrompt] = useState("请对上传的临床数据进行描述性统计并绘制分布图。");
  const [taskType, setTaskType] = useState<TaskType>("analysis");
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [providerCredentials, setProviderCredentials] = useState<ProviderCredentialMap>({});
  const [providerError, setProviderError] = useState<string | null>(null);
  const [model, setModel] = useState<string>("");
  

  const [code, setCode] = useState<string>("# 等待生成的 Python 代码将显示在这里\n");

  const [dataset, setDataset] = useState<DatasetUploadResponse | null>(null);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [showDatasetPreview, setShowDatasetPreview] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const [executionResult, setExecutionResult] = useState<CodeExecutionResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [chatMessages, setChatMessages] = useState<WorkspaceChatMessage[]>([]);
  const [chatSessionId, setChatSessionId] = useState<number | null>(null);
  const [isChatting, setIsChatting] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  // 依据语言动态生成“分析类型”选项文本
  const taskTypeOptions = useMemo(
    () => [
      { value: "strategy" as TaskType, label: lang === "en" ? "Strategy" : "分析策略" },
      { value: "analysis" as TaskType, label: lang === "en" ? "Analysis" : "数据分析" },
    ],
    [lang]
  );

  const loadProviderCredentials = useCallback(
    async (force = false) => {
      try {
        const credentials = await fetchProviderCredentials(force);
        setProviderCredentials(credentials);
      } catch (err) {
        console.error("Failed to load provider credentials", err);
        setProviderCredentials({});
      }
    },
    []
  );

  const refreshProviders = useCallback(async () => {
    try {
      const response = await listProviders();
      const sanitized = response
        .map((provider) => ({
          ...provider,
          models:
            provider.id === "openai"
              ? provider.models.filter((modelName) =>
                  ["gpt-4o", "gpt-4o-mini", "gpt-4.1"].includes(modelName)
                )
              : provider.models.filter((item) => Boolean(item)),
        }))
        .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
      setProviders(sanitized);
      setProviderError(null);
    } catch (err) {
      setProviderError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const configuredProviders = useMemo<LLMProviderInfo[]>(() => {
    const entries = Object.entries(providerCredentials);
    if (entries.length === 0) {
      return [];
    }
    return entries
      .map(([providerId, credential]) => {
        const providerInfo =
          providers.find((item) => item.id === providerId) ??
          FALLBACK_PROVIDERS.find((item) => item.id === providerId);
        const available =
          providerInfo?.models ??
          FALLBACK_PROVIDERS.find((item) => item.id === providerId)?.models ??
          [];
        const availableSet = new Set(available.filter(Boolean));
        const configured =
          credential.defaultModels?.map((model) => model.trim()).filter(Boolean) ?? [];
        const hasDefaultModels = configured.length > 0;
        const hasAnyCredential =
          hasDefaultModels || Boolean(credential.apiKey) || Boolean(credential.baseUrl);
        if (!hasAnyCredential) {
          return null;
        }
        let modelsToShow: string[] = [];
        if (hasDefaultModels) {
          const intersection = configured.filter((model) => availableSet.has(model));
          modelsToShow = (intersection.length > 0 ? intersection : configured).filter(Boolean);
        } else {
          modelsToShow = available.filter(Boolean);
        }

        if (modelsToShow.length === 0) {
          const fallbackModels =
            FALLBACK_PROVIDERS.find((item) => item.id === providerId)?.models ?? [];
          modelsToShow = fallbackModels.filter(Boolean);
        }

        const uniqueModels = Array.from(new Set(modelsToShow));
        if (uniqueModels.length === 0) {
          return null;
        }

        return {
          id: providerId,
          name: providerInfo?.name ?? providerId,
          models: uniqueModels,
        };
      })
      .filter((provider): provider is LLMProviderInfo => Boolean(provider))
      .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
  }, [providerCredentials, providers]);

  const DEFAULT_OPENAI_VALUE = "openai:"; // 后端将使用 OpenAI 默认模型（如 GPT-4o）
  const availableModelValues = useMemo(
    () => [
      DEFAULT_OPENAI_VALUE,
      ...configuredProviders.flatMap((provider) =>
        provider.models.map((modelName) => `${provider.id}:${modelName}`)
      ),
    ],
    [configuredProviders]
  );

  const createMessageId = useCallback(
    () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    []
  );

  const datasetContext = useMemo(() => {
    if (!dataset) {
      return undefined;
    }
    const columns = dataset.columns
      .map((col) => `${col} (${dataset.schema[col] ?? "unknown"})`)
      .join(", ");
    return [
      `Dataset: ${dataset.original_filename}`,
      `沙箱内存放文件名: ${dataset.filename}`,
      `Rows: ${dataset.rows}`,
      `Columns: ${columns}`,
      "执行环境会暴露 DATASET_PATH 环境变量指向该数据文件，可直接用于读取。",
    ].join("\n");
  }, [dataset]);

  useEffect(() => {
    if (dataset?.original_filename) {
      setSelectedFileName(dataset.original_filename);
    }
  }, [dataset?.original_filename]);

  useEffect(() => {
    const unsubscribe = subscribeToUserIdChange(() => {
      setDataset(null);
      setSelectedFileName(null);
      setShowDatasetPreview(false);
      setTaskId(null);
      setExecutionResult(null);
      setChatMessages([]);
      setChatSessionId(null);
      setError(null);
      setChatError(null);
      void refreshProviders();
      void loadProviderCredentials(true);
    });
    return () => {
      unsubscribe();
    };
  }, [loadProviderCredentials, refreshProviders]);

  useEffect(() => {
    const handleUpdate = (event: Event) => {
      const detail = (event as CustomEvent<ProviderCredentialMap | undefined>).detail;
      if (detail) {
        setProviderCredentials(detail);
      } else {
        void loadProviderCredentials(true);
      }
      void refreshProviders();
    };
    window.addEventListener(PROVIDER_CREDENTIALS_UPDATED_EVENT, handleUpdate as EventListener);
    return () => {
      window.removeEventListener(
        PROVIDER_CREDENTIALS_UPDATED_EVENT,
        handleUpdate as EventListener
      );
    };
  }, [loadProviderCredentials, refreshProviders]);

  useEffect(() => {
    void refreshProviders();
  }, [refreshProviders]);

  useEffect(() => {
    void loadProviderCredentials(true);
  }, [loadProviderCredentials]);

  // 个人偏好已移除

  useEffect(() => {
    if (!availableModelValues.length) {
      if (model !== "") setModel("");
      return;
    }
    if (!availableModelValues.includes(model)) {
      setModel(availableModelValues[0]);
    }
  }, [availableModelValues, model]);

  const handleGenerate = useCallback(async () => {
    if (!model) {
      setError(L.configModelFirst);
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      const response = await generateCode({
        prompt,
        model,
        taskType,
        datasetContext,
      });
      setCode(response.code ?? "");

      const title = prompt.slice(0, 40) || L.unnamed;
      const createdTask = await createTask({
        title,
        prompt,
        model: response.model || model,
        generated_code: response.code,
        dataset_filename: dataset?.filename,
      });
      setTaskId(createdTask.id);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, model, taskType, datasetContext, dataset?.filename]);

  const handleExecute = useCallback(async () => {
    if (!code) {
      setError(L.needCode);
      return;
    }
    setIsRunning(true);
    setError(null);
    try {
      const payload: CodeExecutionPayload = {
        code,
        taskId: taskId ?? undefined,
        datasetFilename: dataset?.filename,
      };
      const result = await executeCode(payload);
      setExecutionResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }, [code, dataset?.filename, taskId]);

  const handleDatasetUpload = useCallback(async (file: File) => {
    setError(null);
    try {
      const response = await uploadDataset(file);
      setDataset(response);
      setShowDatasetPreview(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const handleFileChange = useCallback(
    async (file?: File) => {
      if (!file) {
        return;
      }
      setSelectedFileName(file.name);
      await handleDatasetUpload(file);
    },
    [handleDatasetUpload]
  );



  const handleChatSend = useCallback(
    async (input: string) => {
      if (!model) {
        setChatError(L.configModelForChat);
        return;
      }
      const userMessage: WorkspaceChatMessage = {
        id: createMessageId(),
        role: "user",
        content: input,
      };

      const pendingHistory = [...chatMessages, userMessage];
      setChatMessages(pendingHistory);
      setIsChatting(true);
      setChatError(null);

      const payloadMessages: ChatMessagePayload[] = pendingHistory.map((message) => ({
        role: message.role,
        content: message.content,
      }));

      try {
        const response = await sendChat({
          model,
          sessionId: chatSessionId ?? undefined,
          taskId: taskId ?? undefined,
          messages: payloadMessages,
          context: {
            code_snapshot: code,
            stdout: executionResult?.stdout ?? null,
            stderr: executionResult?.stderr ?? null,
          },
        });

        setChatSessionId(response.session_id);
        const assistantMessage: WorkspaceChatMessage = {
          id: createMessageId(),
          role: "assistant",
          content: response.message.content,
          reasoning: response.reasoning ?? null,
          patch: response.patch ?? null,
          usage: response.usage ?? undefined,
        };
        setChatMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        setChatError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsChatting(false);
      }
    },
    [
      chatMessages,
      model,
      chatSessionId,
      taskId,
      code,
      executionResult,
      createMessageId,
    ]
  );

  const handleApplyPatch = useCallback((message: WorkspaceChatMessage) => {
    if (!message.patch) {
      return;
    }
    const patchText = message.patch;
    setChatError(null);
    setCode((prev) => {
      let patchBody = patchText.trim();

      if (patchBody.startsWith("```")) {
        const lines = patchBody.split("\n");
        lines.shift();
        if (lines.length > 0 && lines[lines.length - 1].trim() === "```") {
          lines.pop();
        }
        patchBody = lines.join("\n");
      }

      const looksLikeDiff = isDiffPatch(patchBody);
      if (looksLikeDiff) {
        const applied = applyTextPatch(prev, patchBody, { fuzzFactor: 1 });
        if (applied !== false) {
          return applied;
        }

        const snippets = extractSnippetsFromDiff(patchBody);
        if (snippets.length > 0) {
          const mergedResult = mergeMultipleSnippets(prev, snippets);
          if (mergedResult !== null) {
            return mergedResult;
          }
        }
      }

      const merged = mergeFunctionOrClassSnippet(prev, patchBody);
      if (merged) {
        return merged;
      }

      const generatedPatch = createTwoFilesPatch(
        "analysis.py",
        "analysis.py",
        prev,
        patchBody,
        "",
        "",
        { context: 3 }
      );
      const appliedFromGenerated = applyTextPatch(prev, generatedPatch);
      if (appliedFromGenerated !== false) {
        return appliedFromGenerated;
      }

      setChatError(L.patchCannotMerge);
      return prev;
    });
  }, []);


  useEffect(() => {
    if (!taskId || chatSessionId || chatMessages.length > 0) {
      return;
    }
    let cancelled = false;

    (async () => {
      try {
        const sessions = await listChatSessions(taskId);
        if (cancelled || sessions.length === 0) {
          return;
        }
        const activeSession = sessions[0];
        const history = await getChatSession(activeSession.id);
        if (cancelled) {
          return;
        }
        setChatSessionId(history.session.id);
        const restored: WorkspaceChatMessage[] = history.messages
          .filter((msg) => msg.role === "user" || msg.role === "assistant")
          .map((msg) => ({
            id: createMessageId(),
            role: msg.role as WorkspaceChatMessage["role"],
            content: msg.content,
            reasoning: msg.reasoning ?? null,
            patch: msg.patch ?? null,
            usage: msg.usage ?? undefined,
          }));
        setChatMessages(restored);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load chat history", err);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [taskId, chatSessionId, chatMessages.length, createMessageId]);

  useEffect(() => {
    setChatMessages([]);
    setChatSessionId(null);
  }, [model]);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-white">{L.title}</h1>
        <p className="text-sm text-slate-400">{L.desc}</p>
      </header>

      {error ? <Alert tone="error" title={L.reqFailed} message={error} /> : null}
      {providerError ? (
        <Alert tone="error" title={L.providerFailed} message={providerError} />
      ) : null}
      <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="grid gap-4 lg:grid-cols-12 lg:items-start">
          {/* 任务描述：左侧 */}
          <div className="lg:col-span-5 space-y-2">
            <label className="text-sm font-medium text-white">{L.taskDesc}</label>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="h-32 w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand"
              placeholder={lang === "zh" ? "例如：对血压与年龄的关系进行回归分析，并绘制散点图。" : "e.g., Run a regression between age and blood pressure and draw a scatter plot."}
            />
          </div>

          {/* 模型 + 分析类型：中间列，纵向堆叠 */}
          <div className="lg:col-span-3 space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-white">{L.chooseModel}</label>
            <select
              className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              {/* 默认模型（OpenAI 后端默认）始终提供 */}
              <option value={DEFAULT_OPENAI_VALUE} className="bg-slate-900 text-slate-200">
                {L.defaultModel}
              </option>
              {configuredProviders.length > 0 ? (
                configuredProviders.map((provider) => (
                  <optgroup key={provider.id} label={provider.name}>
                    {provider.models.map((modelName) => {
                      const value = `${provider.id}:${modelName}`;
                      return (
                        <option key={value} value={value} className="bg-slate-900 text-slate-200">
                          {modelName}
                        </option>
                      );
                    })}
                  </optgroup>
                ))
              ) : null}
            </select>
            {configuredProviders.length === 0 ? (
              <div className="mt-1 space-y-1">
                <p className="text-xs text-rose-300">{L.needProviderModels}</p>
                <p className="text-xs text-slate-500">{L.defaultHint}</p>
              </div>
            ) : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-white">{L.analysisType}</label>
              <select
                key={lang}
                className="w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
                value={taskType}
                onChange={(event) => setTaskType(event.target.value as TaskType)}
              >
                {taskTypeOptions.map((item) => (
                  <option
                    key={`${lang}-${item.value}`}
                    value={item.value}
                    className="bg-slate-900 text-slate-200"
                  >
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 数据集：模型右侧对齐 */}
          <div className="lg:col-span-3 space-y-2">
            <label className="text-sm font-medium text-white">{L.dataset}</label>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-2 rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-xs text-slate-300">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(event) => {
                    void handleFileChange(event.target.files?.[0]);
                  }}
                  className="hidden"
                />
                <button
                  type="button"
                  className="rounded-md bg-brand px-3 py-2 text-xs font-medium text-white transition hover:bg-brand-light disabled:cursor-not-allowed disabled:bg-slate-700"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {L.pickData}
                </button>
                <span className="flex-1 truncate text-left">
                  {selectedFileName || dataset?.original_filename || L.noFile}
                </span>
              </div>
              {dataset ? (
                <button
                  type="button"
                  onClick={() => setShowDatasetPreview((prev) => !prev)}
                  className="flex items-center gap-2 rounded-md border border-slate-600 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-brand"
                  aria-label={showDatasetPreview ? L.previewHide : L.previewShow}
                >
                  {showDatasetPreview ? <EyeOff size={14} /> : <Eye size={14} />}
                  <span>{showDatasetPreview ? L.previewToggleHide : L.previewToggleShow}</span>
                </button>
              ) : null}
            </div>
            {dataset ? (
              <p className="text-xs text-slate-400">
                {L.uploaded} {dataset.original_filename} ({L.colsLabel} {dataset.columns.length}, {L.rowsLabel} {dataset.rows})
              </p>
            ) : (
              <p className="text-xs text-slate-500">{L.csvSupport}</p>
            )}

            {/* 生成按钮：紧跟在数据集下方 */}
            <button
              type="button"
              onClick={() => void handleGenerate()}
              className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-light disabled:cursor-not-allowed disabled:bg-slate-700"
              disabled={isGenerating}
            >
              {isGenerating ? L.generating : L.genCode}
            </button>
          </div>

        </div>
      </section>

      {dataset && showDatasetPreview ? (
        <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">{lang === "zh" ? "数据预览" : "Preview"}</h3>
            <button
              type="button"
              onClick={() => setShowDatasetPreview(false)}
              className="rounded-md bg-brand p-2 text-white transition hover:bg-brand-light"
              aria-label={L.previewHide}
            >
              <EyeOff size={16} />
            </button>
          </div>
          <div className="mt-3 max-h-72 overflow-auto text-xs">
            <table className="w-full border-collapse">
              <thead className="sticky top-0 bg-slate-900 text-left text-slate-300">
                <tr>
                  {dataset.columns.map((col) => (
                    <th key={col} className="border border-slate-800 px-2 py-1">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataset.preview.slice(0, 20).map((row, idx) => (
                  <tr key={idx} className="odd:bg-slate-900 even:bg-slate-950/60">
                    {dataset.columns.map((col) => (
                      <td key={col} className="border border-slate-800 px-2 py-1">
                        {String((row as Record<string, unknown>)[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-3 lg:h-[640px]">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">{L.pyCode}</h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void handleExecute()}
                className="rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-medium text-slate-900 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700"
                disabled={isRunning}
              >
                {isRunning ? L.running : L.runNow}
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden rounded-lg border border-slate-800">
            <MonacoEditor
              height="100%"
              language="python"
              theme="vs-dark"
              value={code}
              onChange={(value) => setCode(value ?? "")}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                automaticLayout: true,
              }}
            />
          </div>
        </div>

        <ChatPanel
          messages={chatMessages}
          isLoading={isChatting}
          onSend={handleChatSend}
          disabled={isChatting}
          error={chatError}
          className="lg:h-[640px]"
          onApplyPatch={handleApplyPatch}
        />

        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">{L.execResult}</h3>
              {taskId ? (
                <span className="text-xs text-slate-500">{L.taskIdLbl}{taskId}</span>
              ) : null}
            </div>
            {executionResult ? (
              <div className="mt-3 space-y-3">
                <div>
                  <h4 className="text-xs font-semibold text-slate-400">{L.status}</h4>
                  <p className="text-sm text-white">{executionResult.status}</p>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-400">{L.stdout}</h4>
                  <pre className="mt-1 max-h-40 overflow-auto rounded bg-slate-950 p-3 text-xs">
                    {executionResult.stdout || L.noOutput}
                  </pre>
                </div>
                {executionResult.stderr ? (
                  <div>
                    <h4 className="text-xs font-semibold text-rose-300">{L.stderr}</h4>
                    <pre className="mt-1 max-h-32 overflow-auto rounded bg-rose-950/40 p-3 text-xs text-rose-200">
                      {executionResult.stderr}
                    </pre>
                  </div>
                ) : null}
                {executionResult.artifacts && executionResult.artifacts.length > 0 ? (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400">{L.artifacts}</h4>
                    <div className="mt-2 grid gap-3">
                      {executionResult.artifacts.map((artifact) => {
                        const href = artifact.url.startsWith("http")
                          ? artifact.url
                          : `${API_BASE_URL}${artifact.url}`;
                        const isImage = artifact.mimetype?.startsWith("image/") ?? false;
                        return (
                          <div
                            key={`${artifact.filename}-${href}`}
                            className="overflow-hidden rounded-md border border-slate-800 bg-slate-950/60"
                          >
                            <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-xs text-slate-300">
                              <span className="truncate" title={artifact.filename}>
                                {artifact.filename}
                              </span>
                              <a
                                href={href}
                                target="_blank"
                                rel="noreferrer"
                                className="text-brand hover:text-brand-light"
                              >
                                {L.view}
                              </a>
                            </div>
                            {isImage ? (
                              <div className="flex justify-center bg-slate-900/40 p-2">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={href}
                                  alt={artifact.filename}
                                  className="max-h-56 w-auto rounded"
                                />
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">{L.waiting}</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
