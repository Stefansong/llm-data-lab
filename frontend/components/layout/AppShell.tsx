"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";

import {
  AuthClaims,
  readAccessTokenClaims,
  subscribeToAccessTokenChange,
  writeAccessToken,
} from "@/lib/authToken";
import { clearActiveUserId } from "@/lib/userProfile";
import { LANG_UPDATED_EVENT, readLang, writeLang, type Lang } from "@/lib/i18n";

const links = [
  { href: "/", label: "首页" },
  { href: "/workspace", label: "数据工作台" },
  { href: "/history", label: "历史记录" },
  { href: "/settings", label: "设置" },
] as const;

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [claims, setClaims] = useState<AuthClaims | null>(null);
  const [lang, setLang] = useState<Lang>("zh");

  useEffect(() => {
    setClaims(readAccessTokenClaims());
    const unsubscribe = subscribeToAccessTokenChange((_token, nextClaims) => {
      setClaims(nextClaims);
    });
    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    setLang(readLang());
    const onUpdate = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onUpdate);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onUpdate);
  }, []);

  const handleLogout = () => {
    writeAccessToken(null);
    clearActiveUserId();
    router.replace("/auth");
  };

  const navLinks = useMemo(
    () =>
      links.map((link) => {
        const isActive = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-1 transition ${
              isActive
                ? "bg-brand/20 text-white"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            {link.label}
          </Link>
        );
      }),
    [pathname]
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-white">
            <span className="rounded bg-brand px-2 py-1 text-xs uppercase tracking-widest">LLM</span>
            Data Lab
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <div className="flex gap-2 text-slate-300">{navLinks}</div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => writeLang(lang === "zh" ? "en" : "zh")}
                className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-200 transition hover:border-brand"
                title={lang === "zh" ? "Switch to English" : "切换到中文"}
              >
                {lang === "zh" ? "中文/EN" : "EN/中文"}
              </button>
            </div>
            {claims ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">已登录：{claims.username}</span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-200 transition hover:border-rose-400 hover:text-rose-300"
                >
                  退出
                </button>
              </div>
            ) : (
              <Link
                href="/auth"
                className="rounded-md border border-brand/50 px-3 py-1 text-xs text-brand transition hover:bg-brand/10 hover:text-white"
              >
                登录 / 注册
              </Link>
            )}
          </nav>
        </div>
      </header>
      <main className="pb-16 pt-10">{children}</main>
    </div>
  );
}
