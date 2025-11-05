import { Loader2 } from "lucide-react";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Spinner({ size = "md", className = "" }: SpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  return (
    <Loader2
      className={`animate-spin ${sizeClasses[size]} ${className}`}
      aria-label="Loading"
    />
  );
}

interface LoadingMessageProps {
  message: string;
  size?: "sm" | "md" | "lg";
}

export function LoadingMessage({ message, size = "md" }: LoadingMessageProps) {
  return (
    <div className="flex items-center justify-center gap-2 text-slate-400">
      <Spinner size={size} />
      <span className="text-sm">{message}</span>
    </div>
  );
}
