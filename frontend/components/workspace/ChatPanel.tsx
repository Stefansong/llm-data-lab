"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { LANG_UPDATED_EVENT, chatTexts, readLang, type Lang } from "@/lib/i18n";
import { LoadingMessage } from "@/components/ui/Spinner";

export type WorkspaceChatRole = "user" | "assistant";

export interface WorkspaceChatMessage {
  id: string;
  role: WorkspaceChatRole;
  content: string;
  reasoning?: string | null;
  patch?: string | null;
  usage?: Record<string, unknown> | null;
}

interface ChatPanelProps {
  messages: WorkspaceChatMessage[];
  isLoading: boolean;
  onSend: (message: string) => Promise<void> | void;
  disabled?: boolean;
  error?: string | null;
  className?: string;
  onApplyPatch?: (message: WorkspaceChatMessage) => void;
}

export function ChatPanel({
  messages,
  isLoading,
  onSend,
  disabled,
  error,
  className,
  onApplyPatch,
}: ChatPanelProps) {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const T = useMemo(() => chatTexts[lang], [lang]);
  const [input, setInput] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const value = input.trim();
    if (!value || disabled) {
      return;
    }
    setInput("");
    await onSend(value);
  };

  return (
    <div
      className={`flex h-full flex-col rounded-lg border border-slate-800 bg-slate-900/40 ${
        className ?? ""
      }`}
    >
      <div className="border-b border-slate-800 px-4 py-3">
        <h3 className="text-sm font-semibold text-white">{T.title}</h3>
        <p className="mt-1 text-xs text-slate-400">{T.subtitle}</p>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <p className="text-xs text-slate-500">{T.empty}</p>
        ) : (
          messages.map((message) => {
            const isAssistant = message.role === "assistant";
            const bubbleClasses = isAssistant
              ? "border border-brand/40 bg-brand/10 text-white"
              : "border border-slate-800 bg-slate-950/70 text-slate-200";

            // Frontend fallback: some providers may return the whole JSON as content.
            // Try to parse and extract reply/patch/reasoning if message.patch is missing.
            let contentText = message.content;
            let reasoningText: string | null | undefined = message.reasoning ?? null;
            let patchText: string | null | undefined = message.patch ?? null;
            const tryParseStructured = (raw: string) => {
              const trim = raw.trim();
              const stripFence = (txt: string) => {
                const t = txt.trim();
                if (!t.startsWith("```")) return txt;
                const lines = t.split("\n");
                lines.shift();
                if (lines.length && lines[lines.length - 1].trim() === "```") lines.pop();
                return lines.join("\n");
              };
              const cleaned = stripFence(trim);
              try {
                const obj = JSON.parse(cleaned);
                if (obj && typeof obj === "object" && "reply" in obj) {
                  return {
                    reply: String(obj.reply ?? ""),
                    patch: typeof obj.patch === "string" ? obj.patch : null,
                    reasoning: typeof obj.reasoning === "string" ? obj.reasoning : null,
                  };
                }
              } catch (_) {
                // ignore
              }
              return null;
            };
            if (isAssistant && (!patchText || typeof patchText !== "string")) {
              const parsed = tryParseStructured(message.content);
              if (parsed) {
                contentText = parsed.reply;
                reasoningText = parsed.reasoning;
                patchText = parsed.patch;
              }
            }
            return (
              <div key={message.id} className={`rounded-md px-3 py-2 text-sm ${bubbleClasses}`}>
                <p className="whitespace-pre-wrap leading-relaxed">{contentText}</p>
                {reasoningText ? (
                  <p className="mt-2 rounded bg-slate-950/60 px-3 py-2 text-xs text-slate-400">
                    {reasoningText}
                  </p>
                ) : null}
                {patchText ? (
                  <div className="mt-2 space-y-2">
                    <pre className="max-h-40 overflow-auto rounded bg-slate-950/80 p-3 text-xs text-emerald-200">
                      {patchText}
                    </pre>
                    {onApplyPatch ? (
                      <button
                        type="button"
                        onClick={() => onApplyPatch({ ...message, patch: patchText || undefined })}
                        className="rounded border border-emerald-500/60 px-2 py-1 text-xs text-emerald-200 transition hover:bg-emerald-500/10"
                        disabled={disabled || isLoading}
                      >
                        {T.applyToEditor}
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
        {isLoading ? <LoadingMessage message={T.thinking} size="sm" /> : null}
        {error ? <p className="text-xs text-rose-300">{error}</p> : null}
      </div>
      <form onSubmit={handleSubmit} className="space-y-2 border-t border-slate-800 px-4 py-3">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={T.placeholder}
          className="h-20 w-full rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand"
          disabled={disabled}
        />
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{T.autoAttach}</span>
          <button
            type="submit"
            className="rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-white transition hover:bg-brand-light disabled:cursor-not-allowed disabled:bg-slate-700"
            disabled={disabled || isLoading}
          >
            {isLoading ? T.sending : T.send}
          </button>
        </div>
      </form>
    </div>
  );
}
