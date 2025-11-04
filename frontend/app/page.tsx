"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { LANG_UPDATED_EVENT, homeTexts, readLang, type Lang } from "@/lib/i18n";

export default function HomePage() {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const T = homeTexts[lang];
  const features = useMemo(
    () => [
      { title: T.featureTitle, body: T.featureBody },
      {
        title: lang === "zh" ? "一键执行科研分析" : "One‑click Analysis",
        body:
          lang === "zh"
            ? "自动完成数据清洗、统计建模、可视化绘图，输出可复现的 Python 脚本。"
            : "Automate cleaning, modeling and visualization with reproducible Python scripts.",
      },
      {
        title: lang === "zh" ? "科研工作台" : "Workspace",
        body:
          lang === "zh"
            ? "上传数据、生成代码、执行任务、查看历史记录于一体的协同平台。"
            : "Upload data, generate code, run tasks and review history in one place.",
      },
    ],
    [T, lang]
  );

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-16 px-6 py-16">
      <section className="flex flex-col items-start gap-6">
        <span className="rounded-full border border-brand-light px-3 py-1 text-xs uppercase tracking-widest text-brand-light">LLM Data Lab</span>
        <h1 className="text-4xl font-semibold leading-tight text-white md:text-5xl">
          {lang === "zh" ? "让多模型 LLM 与 Python 沙箱成为你的科研助手" : "Let multi‑model LLMs and a Python sandbox power your research"}
        </h1>
        <p className="max-w-2xl text-lg text-slate-300">
          {lang === "zh"
            ? "LLM Data Lab 将自然语言需求转化为可靠的 Python 分析流水线。比较不同模型的代码，安全执行并可视化结果，沉淀每一次科研灵感。"
            : "Turn natural‑language requests into reliable Python pipelines. Compare models, run safely and visualize results."}
        </p>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/workspace"
            className="rounded-md bg-brand px-5 py-2 text-sm font-medium text-white shadow-lg shadow-brand/30 transition hover:bg-brand-light"
          >
            {T.ctaWorkspace}
          </Link>
          <Link
            href="/history"
            className="rounded-md border border-slate-700 px-5 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
          >
            {T.ctaHistory}
          </Link>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <div key={feature.title} className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
            <p className="mt-3 text-sm text-slate-300">{feature.body}</p>
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-300">
        <h2 className="text-xl font-semibold text-white">{T.howTitle}</h2>
        <ol className="mt-4 space-y-3">
          {T.steps.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
