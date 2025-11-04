interface AlertProps {
  title?: string;
  message: string;
  tone?: "info" | "success" | "error";
}

const toneStyles: Record<NonNullable<AlertProps["tone"]>, string> = {
  info: "border-slate-700 bg-slate-900/50 text-slate-200",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  error: "border-rose-500/40 bg-rose-500/10 text-rose-200",
};

export function Alert({ title, message, tone = "info" }: AlertProps) {
  return (
    <div className={`rounded-md border px-4 py-3 text-sm ${toneStyles[tone]}`}>
      {title ? <p className="font-medium text-white">{title}</p> : null}
      <p className="mt-1 leading-relaxed">{message}</p>
    </div>
  );
}
