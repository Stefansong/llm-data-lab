"use client";

import { useEffect, useMemo, useState } from "react";

import { AnalysisTask, getTask, listHistory } from "@/lib/api";
import { Alert } from "@/components/ui/Alert";
import { subscribeToUserIdChange } from "@/lib/userProfile";
import { LANG_UPDATED_EVENT, historyTexts, readLang, type Lang } from "@/lib/i18n";

const statusColors: Record<AnalysisTask["status"], string> = {
  queued: "bg-slate-700 text-slate-200",
  running: "bg-amber-500/20 text-amber-200",
  succeeded: "bg-emerald-500/20 text-emerald-200",
  failed: "bg-rose-500/20 text-rose-200",
};

export function HistoryClient() {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const T = useMemo(() => historyTexts[lang], [lang]);
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AnalysisTask | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  useEffect(() => {
    let disposed = false;

    const resetDetail = () => {
      setSelectedTask(null);
      setIsDetailOpen(false);
      setDetailError(null);
    };

    const fetchTasks = () => {
      setIsLoading(true);
      setError(null);
      resetDetail();
      void listHistory()
        .then((response) => {
          if (!disposed) {
            setTasks(response);
          }
        })
        .catch((err) => {
          if (!disposed) {
            setError(err instanceof Error ? err.message : String(err));
          }
        })
        .finally(() => {
          if (!disposed) {
            setIsLoading(false);
          }
        });
    };

    fetchTasks();
    const unsubscribe = subscribeToUserIdChange(() => {
      fetchTasks();
    });

    return () => {
      disposed = true;
      unsubscribe();
    };
  }, []);

  const handleViewTask = (taskId: number) => {
    setIsDetailOpen(true);
    const existing = tasks.find((item) => item.id === taskId);
    if (existing) {
      setSelectedTask(existing);
    }
    setIsDetailLoading(true);
    setDetailError(null);
    void getTask(taskId)
      .then((response) => {
        setSelectedTask(response);
        setTasks((prev) => prev.map((task) => (task.id === response.id ? response : task)));
      })
      .catch((err) => {
        setDetailError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setIsDetailLoading(false));
  };

  const handleCloseDetail = () => {
    setIsDetailOpen(false);
    setSelectedTask(null);
    setDetailError(null);
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 px-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-white">{T.title}</h1>
        <p className="text-sm text-slate-400">{T.desc}</p>
      </header>

      {error ? <Alert tone="error" title={T.fetchFailed} message={error} /> : null}

      <div className="rounded-xl border border-slate-800 bg-slate-900/40">
        <table className="w-full border-collapse text-sm">
          <thead className="bg-slate-900 text-xs uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left">{T.task}</th>
              <th className="px-4 py-3 text-left">{T.model}</th>
              <th className="px-4 py-3 text-left">{T.status}</th>
              <th className="px-4 py-3 text-left">{T.createdAt}</th>
              <th className="px-4 py-3 text-left">{T.summary}</th>
              <th className="px-4 py-3 text-left">{T.action}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  {T.loading}
                </td>
              </tr>
            ) : null}
            {!isLoading && tasks.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  {T.empty}
                </td>
              </tr>
            ) : null}
            {tasks.map((task) => (
              <tr key={task.id} className="border-t border-slate-800">
                <td className="px-4 py-3 text-white">
                  <p className="font-medium">{task.title}</p>
                  <p className="mt-1 text-xs text-slate-400">{task.prompt}</p>
                </td>
                <td className="px-4 py-3 text-slate-300">{task.model}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-3 py-1 text-xs ${statusColors[task.status]}`}>
                    {task.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {new Date(task.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {task.summary ?? task.execution_stdout?.slice(0, 120) ?? "-"}
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => handleViewTask(task.id)}
                    className="rounded-md border border-slate-700 px-3 py-1 text-xs font-medium text-slate-200 transition hover:border-brand hover:text-brand"
                  >
                    {T.view}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isDetailOpen ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center px-4 py-8">
          <div className="absolute inset-0 bg-black/60" onClick={handleCloseDetail} aria-hidden="true" />
          <div className="relative z-50 flex w-full max-w-4xl max-h-[85vh] flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900/95 text-sm text-slate-200 shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-slate-800 bg-slate-900/80 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold text-white">{T.task}</h2>
                {selectedTask ? (
                  <p className="mt-1 text-xs text-slate-400">
                    {T.detailTaskId}{selectedTask.id} · {T.createdAtOn} {new Date(selectedTask.created_at).toLocaleString()}
                  </p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:border-rose-400 hover:text-rose-300"
              >
                {T.close}
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              {isDetailLoading ? <Alert tone="info" message={T.loading} /> : null}
              {detailError ? <Alert tone="error" title={T.detailFailed} message={detailError} /> : null}

              {selectedTask ? (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-xs text-slate-400">{T.modelLbl}</p>
                      <p className="text-sm text-white">{selectedTask.model}</p>
                    </div>
                    <div>
                    <p className="text-xs text-slate-400">{T.statusLbl}</p>
                    <span
                      className={`mt-1 inline-flex rounded-full px-3 py-1 text-xs ${statusColors[selectedTask.status] || "bg-slate-700 text-slate-200"}`}
                    >
                      {selectedTask.status}
                    </span>
                  </div>
                  {selectedTask.dataset_filename ? (
                    <div className="md:col-span-2">
                      <p className="text-xs text-slate-400">{T.datasetFile}</p>
                      <p className="text-sm text-white">{selectedTask.dataset_filename}</p>
                    </div>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <p className="text-xs text-slate-400">{T.taskDesc}</p>
                  <p className="rounded-md border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
                    {selectedTask.prompt || "-"}
                  </p>
                </div>

                {selectedTask.generated_code ? (
                  <div className="space-y-2">
                    <p className="text-xs text-slate-400">{T.genCode}</p>
                    <pre className="max-h-64 overflow-auto rounded-md border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
                      {selectedTask.generated_code}
                    </pre>
                  </div>
                ) : null}

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <p className="text-xs text-slate-400">{T.stdoutLbl}</p>
                    <pre className="max-h-56 overflow-auto rounded-md border border-slate-800 bg-slate-950/80 p-3 text-xs text-emerald-200">
                      {selectedTask.execution_stdout || T.noOutput}
                    </pre>
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs text-slate-400">{T.stderrLbl}</p>
                    <pre className="max-h-56 overflow-auto rounded-md border border-slate-800 bg-rose-950/40 p-3 text-xs text-rose-200">
                      {selectedTask.execution_stderr || T.noError}
                    </pre>
                  </div>
                </div>
              </div>
            ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
