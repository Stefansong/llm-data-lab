import { AuthGuard } from "@/components/auth/AuthGuard";
import { SettingsClient } from "@/components/settings/SettingsClient";

export const metadata = {
  title: "设置 | LLM Data Lab",
};

export default function SettingsPage() {
  return (
    <AuthGuard>
      <SettingsClient />
    </AuthGuard>
  );
}
