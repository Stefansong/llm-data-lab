"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import {
  PROVIDER_CREDENTIALS_UPDATED_EVENT,
  ProviderCredential,
  ProviderCredentialMap,
  fetchProviderCredentials,
  saveProviderCredentials,
} from "@/lib/providerSettings";
import { AuthClaims } from "@/lib/authToken";
import { LANG_UPDATED_EVENT, readLang, settingsTexts, type Lang } from "@/lib/i18n";

// 个人偏好功能已移除

type ProviderCredentialForm = {
  apiKey: string;
  baseUrl: string;
  defaultModels: string;
};

const PROVIDER_ITEMS: Array<{
  id: string;
  label: string;
  description: string;
  allowBaseUrl?: boolean;
  basePlaceholder?: string;
  modelPlaceholder?: string;
}> = [
  {
    id: "openai",
    label: "OpenAI",
    description: "GPT-4o / GPT-4.1 / o1 系列模型",
    modelPlaceholder: "gpt-4o,gpt-4o-mini,gpt-4.1",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "深度求索（国内）",
    allowBaseUrl: true,
    basePlaceholder: "https://api.deepseek.com",
    modelPlaceholder: "deepseek-chat,deepseek-coder",
  },
  {
    id: "qwen",
    label: "Qwen (DashScope)",
    description: "通义千问",
    allowBaseUrl: true,
    basePlaceholder: "https://dashscope.aliyuncs.com",
    modelPlaceholder: "qwen-turbo,qwen-plus,qwen-max",
  },
  {
    id: "siliconflow",
    label: "SiliconFlow",
    description: "硅基流动开放平台",
    allowBaseUrl: true,
    basePlaceholder: "https://api.siliconflow.cn",
    modelPlaceholder: "siliconflow-chat,siliconflow-coder",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Claude 3 系列",
    modelPlaceholder: "claude-3-sonnet-20240229,claude-3-haiku-20240307",
  },
];

export function SettingsClient() {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const L = settingsTexts[lang];
  const [providerForms, setProviderForms] = useState<Record<string, ProviderCredentialForm>>({});
  const [providerSaved, setProviderSaved] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [claims] = useState<AuthClaims | null>(null);

  const mapCredentialsToForms = useCallback((credentials: ProviderCredentialMap) => {
    const forms: Record<string, ProviderCredentialForm> = {};
    PROVIDER_ITEMS.forEach((item) => {
      const entry = credentials[item.id] ?? {};
      forms[item.id] = {
        apiKey: entry.apiKey ?? "",
        baseUrl: entry.baseUrl ?? "",
        defaultModels: entry.defaultModels?.join(", ") ?? "",
      };
    });
    return forms;
  }, []);

  // 个人偏好逻辑已移除

  useEffect(() => {
    let cancelled = false;

    const load = async (force = false) => {
      try {
        const credentials = await fetchProviderCredentials(force);
        if (!cancelled) {
          setProviderForms(mapCredentialsToForms(credentials));
          setProviderError(null);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load provider credentials", error);
          setProviderError("无法加载 API 配置，请稍后重试。");
        }
      }
    };

    void load(true);

    const handleUpdate = (event: Event) => {
      const detail = (event as CustomEvent<ProviderCredentialMap | undefined>).detail;
      if (detail) {
        setProviderForms(mapCredentialsToForms(detail));
        setProviderError(null);
      } else {
        void load(true);
      }
    };

    window.addEventListener(PROVIDER_CREDENTIALS_UPDATED_EVENT, handleUpdate as EventListener);

    return () => {
      cancelled = true;
      window.removeEventListener(PROVIDER_CREDENTIALS_UPDATED_EVENT, handleUpdate as EventListener);
    };
  }, [mapCredentialsToForms]);
  // 无个人偏好保存

  const handleProviderChange = useCallback(
    (providerId: string, field: keyof ProviderCredentialForm, value: string) => {
      setProviderForms((prev) => {
        const existing = prev[providerId] ?? { apiKey: "", baseUrl: "", defaultModels: "" };
        return {
          ...prev,
          [providerId]: {
            ...existing,
            [field]: value,
          },
        };
      });
    },
    []
  );

  const handleSaveProviderCredentials = async () => {
    const normalized: ProviderCredentialMap = {};
    Object.entries(providerForms).forEach(([providerId, form]) => {
      const apiKey = form.apiKey.trim();
      const baseUrl = form.baseUrl.trim();
      const models = form.defaultModels
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean);

      const entry: ProviderCredential = {};
      if (apiKey) {
        entry.apiKey = apiKey;
      }
      if (baseUrl) {
        entry.baseUrl = baseUrl;
      }
      if (models.length > 0) {
        entry.defaultModels = models;
      }
      if (Object.keys(entry).length > 0) {
        normalized[providerId] = entry;
      }
    });

    try {
      const updated = await saveProviderCredentials(normalized);
      setProviderForms(mapCredentialsToForms(updated));
      setProviderSaved(true);
      setProviderError(null);
      setTimeout(() => setProviderSaved(false), 2000);
    } catch (error) {
      console.error("Failed to save provider credentials", error);
      setProviderError("保存失败，请稍后再试。");
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-white">{L.title}</h1>
        <p className="text-sm text-slate-400">{L.desc}</p>
      </header>

      {providerSaved ? <Alert tone="success" message={L.saved} /> : null}
      {providerError ? <Alert tone="error" title={L.failed} message={providerError} /> : null}

      <section className="grid gap-6 md:grid-cols-1">
        <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-300">
          <h2 className="text-lg font-semibold text-white">{L.apiTitle}</h2>
          <p className="text-xs text-slate-400">
            所有凭证会加密存储在服务器，仅当前账户可见。生成代码或对话时会自动读取这些配置，无需重复填写。
          </p>
          <div className="grid gap-3">
            {PROVIDER_ITEMS.map((provider) => {
              const form = providerForms[provider.id] ?? {
                apiKey: "",
                baseUrl: "",
                defaultModels: "",
              };
              return (
                <div
                  key={provider.id}
                  className="space-y-3 rounded-lg border border-slate-800 bg-slate-950/40 p-4"
                >
                  <div>
                    <h3 className="text-sm font-semibold text-white">{provider.label}</h3>
                    <p className="text-xs text-slate-400">{provider.description}</p>
                  </div>
                  <label className="block text-xs font-medium text-slate-300">
                    API Key
                    <input
                      type="password"
                      value={form.apiKey}
                      onChange={(event) => handleProviderChange(provider.id, "apiKey", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
                      placeholder="sk-..."
                    />
                  </label>
                  {provider.allowBaseUrl ? (
                  <label className="block text-xs font-medium text-slate-300">
                    {L.baseUrl}
                      <input
                        type="text"
                        value={form.baseUrl}
                        onChange={(event) => handleProviderChange(provider.id, "baseUrl", event.target.value)}
                        className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
                        placeholder={provider.basePlaceholder ?? "https://..."}
                      />
                    </label>
                  ) : null}
                  <label className="block text-xs font-medium text-slate-300">
                    {L.modelList}
                    <textarea
                      value={form.defaultModels}
                      onChange={(event) => handleProviderChange(provider.id, "defaultModels", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100"
                      rows={2}
                      placeholder={provider.modelPlaceholder}
                    />
                  </label>
                </div>
              );
            })}
          </div>
          <button
            type="button"
            onClick={() => void handleSaveProviderCredentials()}
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-light"
          >
            {L.save}
          </button>
          <p className="text-xs text-slate-500">
            保存后将在服务器加密存储。如需确保其它标签页看到最新配置，可刷新页面。
          </p>
        </div>
      </section>

    </div>
  );
}
