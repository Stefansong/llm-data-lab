"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { readAccessToken, subscribeToAccessTokenChange } from "@/lib/authToken";
import { authTexts, LANG_UPDATED_EVENT, readLang, type Lang } from "@/lib/i18n";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [lang, setLang] = useState<Lang>("zh");

  useEffect(() => {
    // Initialize language
    setLang(readLang());

    // Subscribe to language changes
    const handleLangChange = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, handleLangChange);

    return () => {
      window.removeEventListener(LANG_UPDATED_EVENT, handleLangChange);
    };
  }, []);

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
    const T = authTexts[lang];
    return (
      <div className="mx-auto mt-20 max-w-3xl rounded-lg border border-slate-800 bg-slate-900/40 p-6 text-center text-sm text-slate-400">
        {T.verifying}
      </div>
    );
  }

  return <>{children}</>;
}
