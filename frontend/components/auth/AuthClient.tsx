"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { loginUser, registerUser } from "@/lib/api";
import { writeAccessToken } from "@/lib/authToken";
import { writeActiveUserId } from "@/lib/userProfile";
import { LANG_UPDATED_EVENT, authTexts, readLang, type Lang } from "@/lib/i18n";

type Mode = "login" | "register";

export function AuthClient() {
  const [lang, setLang] = useState<Lang>("zh");
  useEffect(() => {
    setLang(readLang());
    const onLang = () => setLang(readLang());
    window.addEventListener(LANG_UPDATED_EVENT, onLang);
    return () => window.removeEventListener(LANG_UPDATED_EVENT, onLang);
  }, []);
  const T = useMemo(() => authTexts[lang], [lang]);
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === "register";

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!username || !password) {
      setError(T.needUserPass);
      return;
    }
    if (isRegister && password !== confirmPassword) {
      setError(T.mismatch);
      return;
    }
    setIsSubmitting(true);
    try {
      const response = isRegister
        ? await registerUser({
            username: username.trim(),
            password,
            email: email.trim() || undefined,
          })
        : await loginUser({
            username: username.trim(),
            password,
          });
      writeAccessToken(response.access_token);
      writeActiveUserId(response.user.id);
      router.replace("/workspace");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(T.fallbackError);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto mt-16 flex max-w-lg flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl">
      <header className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold text-white">{T.title}</h1>
        <p className="text-sm text-slate-400">
          {T.desc}
        </p>
      </header>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`flex-1 rounded-md border px-3 py-2 text-sm transition ${
            mode === "login"
              ? "border-brand bg-brand/10 text-white"
              : "border-slate-700 bg-slate-950/40 text-slate-300 hover:border-brand/60 hover:text-white"
          }`}
        >
          {T.loginTab}
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`flex-1 rounded-md border px-3 py-2 text-sm transition ${
            mode === "register"
              ? "border-brand bg-brand/10 text-white"
              : "border-slate-700 bg-slate-950/40 text-slate-300 hover:border-brand/60 hover:text-white"
          }`}
        >
          {T.registerTab}
        </button>
      </div>

      {error ? <Alert tone="error" title={T.errorTitle} message={error} /> : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block text-sm text-slate-300">
          {T.username}
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-brand"
            placeholder={T.usernamePh}
          />
        </label>

        {isRegister ? (
          <label className="block text-sm text-slate-300">
            {T.email}
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-brand"
              placeholder={T.emailPh}
            />
          </label>
        ) : null}

        <label className="block text-sm text-slate-300">
          {T.password}
          <input
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-brand"
            placeholder={T.passwordPh}
          />
        </label>

        {isRegister ? (
          <label className="block text-sm text-slate-300">
            {T.confirm}
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-brand"
              placeholder={T.confirmPh}
            />
          </label>
        ) : null}

        <button
          type="submit"
          className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-light disabled:cursor-not-allowed disabled:bg-slate-700"
          disabled={isSubmitting}
        >
          {isSubmitting ? T.submitting : isRegister ? T.register : T.login}
        </button>
      </form>
    </div>
  );
}
