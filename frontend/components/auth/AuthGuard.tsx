"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { readAccessToken, subscribeToAccessTokenChange } from "@/lib/authToken";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = readAccessToken();
    if (!token) {
      router.replace("/auth");
      return;
    }
    setReady(true);
    const unsubscribe = subscribeToAccessTokenChange((nextToken) => {
      if (!nextToken) {
        setReady(false);
        router.replace("/auth");
      }
    });
    return () => {
      unsubscribe();
    };
  }, [router]);

  if (!ready) {
    return (
      <div className="mx-auto mt-20 max-w-3xl rounded-lg border border-slate-800 bg-slate-900/40 p-6 text-center text-sm text-slate-400">
        正在校验登录状态...
      </div>
    );
  }

  return <>{children}</>;
}
