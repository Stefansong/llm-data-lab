import { AuthGuard } from "@/components/auth/AuthGuard";
import { WorkspaceClient } from "@/components/workspace/WorkspaceClient";

export const metadata = {
  title: "数据工作台 | LLM Data Lab",
};

export default function WorkspacePage() {
  return (
    <AuthGuard>
      <WorkspaceClient />
    </AuthGuard>
  );
}
