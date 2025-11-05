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

  // Field-level validation errors
  const [fieldErrors, setFieldErrors] = useState<{
    username?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  const isRegister = mode === "register";

  // Validation functions
  const validateEmail = (value: string): string | undefined => {
    if (!value.trim()) return undefined; // Email is optional
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value.trim()) ? undefined : T.emailInvalid;
  };

  const validateUsername = (value: string): string | undefined => {
    if (!value.trim()) return T.needUserPass;
    return value.trim().length >= 3 ? undefined : T.usernameShort;
  };

  const validatePassword = (value: string): string | undefined => {
    if (!value) return T.needUserPass;
    return value.length >= 8 ? undefined : T.passwordShort;
  };

  const validateConfirmPassword = (value: string, passwordValue: string): string | undefined => {
    if (!value) return T.needUserPass;
    return value === passwordValue ? undefined : T.mismatch;
  };

  // Real-time validation handlers
  const handleUsernameBlur = () => {
    setFieldErrors((prev) => ({
      ...prev,
      username: validateUsername(username),
    }));
  };

  const handleEmailBlur = () => {
    setFieldErrors((prev) => ({
      ...prev,
      email: validateEmail(email),
    }));
  };

  const handlePasswordBlur = () => {
    setFieldErrors((prev) => ({
      ...prev,
      password: validatePassword(password),
    }));
  };

  const handleConfirmPasswordBlur = () => {
    setFieldErrors((prev) => ({
      ...prev,
      confirmPassword: validateConfirmPassword(confirmPassword, password),
    }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    // Validate all fields
    const errors: typeof fieldErrors = {};
    errors.username = validateUsername(username);
    errors.password = validatePassword(password);

    if (isRegister) {
      errors.email = validateEmail(email);
      errors.confirmPassword = validateConfirmPassword(confirmPassword, password);
    }

    // Check if there are any errors
    const hasErrors = Object.values(errors).some((err) => err !== undefined);
    if (hasErrors) {
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
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
            onBlur={handleUsernameBlur}
            className={`mt-1 w-full rounded-md border px-3 py-2 text-sm text-white outline-none focus:border-brand ${
              fieldErrors.username
                ? "border-rose-500 bg-slate-950/70"
                : "border-slate-700 bg-slate-950/70"
            }`}
            placeholder={T.usernamePh}
          />
          {fieldErrors.username ? (
            <p className="mt-1 text-xs text-rose-400">{fieldErrors.username}</p>
          ) : null}
        </label>

        {isRegister ? (
          <label className="block text-sm text-slate-300">
            {T.email}
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              onBlur={handleEmailBlur}
              className={`mt-1 w-full rounded-md border px-3 py-2 text-sm text-white outline-none focus:border-brand ${
                fieldErrors.email
                  ? "border-rose-500 bg-slate-950/70"
                  : "border-slate-700 bg-slate-950/70"
              }`}
              placeholder={T.emailPh}
            />
            {fieldErrors.email ? (
              <p className="mt-1 text-xs text-rose-400">{fieldErrors.email}</p>
            ) : null}
          </label>
        ) : null}

        <label className="block text-sm text-slate-300">
          {T.password}
          <input
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onBlur={handlePasswordBlur}
            className={`mt-1 w-full rounded-md border px-3 py-2 text-sm text-white outline-none focus:border-brand ${
              fieldErrors.password
                ? "border-rose-500 bg-slate-950/70"
                : "border-slate-700 bg-slate-950/70"
            }`}
            placeholder={T.passwordPh}
          />
          {fieldErrors.password ? (
            <p className="mt-1 text-xs text-rose-400">{fieldErrors.password}</p>
          ) : null}
        </label>

        {isRegister ? (
          <label className="block text-sm text-slate-300">
            {T.confirm}
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              onBlur={handleConfirmPasswordBlur}
              className={`mt-1 w-full rounded-md border px-3 py-2 text-sm text-white outline-none focus:border-brand ${
                fieldErrors.confirmPassword
                  ? "border-rose-500 bg-slate-950/70"
                  : "border-slate-700 bg-slate-950/70"
              }`}
              placeholder={T.confirmPh}
            />
            {fieldErrors.confirmPassword ? (
              <p className="mt-1 text-xs text-rose-400">{fieldErrors.confirmPassword}</p>
            ) : null}
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
