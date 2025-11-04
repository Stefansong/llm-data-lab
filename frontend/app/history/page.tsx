import { AuthGuard } from "@/components/auth/AuthGuard";
import { HistoryClient } from "@/components/history/HistoryClient";

export const metadata = {
  title: "历史记录 | LLM Data Lab",
};

export default function HistoryPage() {
  return (
    <AuthGuard>
      <HistoryClient />
    </AuthGuard>
  );
}
