"use client";

export type AuthClaims = {
  sub: number;
  username: string;
  exp?: number;
  [key: string]: unknown;
};

export const ACCESS_TOKEN_STORAGE_KEY = "llm-data-lab.access-token";
export const ACCESS_TOKEN_UPDATED_EVENT = "llm-data-lab:access-token-updated";

function safeAtob(value: string): string | null {
  try {
    return typeof window === "undefined" ? null : window.atob(value);
  } catch {
    return null;
  }
}

function parseClaims(token: string): AuthClaims | null {
  const segments = token.split(".");
  if (segments.length !== 3) {
    return null;
  }
  const payload = safeAtob(segments[1]);
  if (!payload) {
    return null;
  }
  try {
    const parsed = JSON.parse(payload);
    const sub = Number(parsed.sub);
    if (!Number.isFinite(sub)) {
      return null;
    }
    return {
      ...parsed,
      sub,
    };
  } catch {
    return null;
  }
}

export function readAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function readAccessTokenClaims(): AuthClaims | null {
  const token = readAccessToken();
  if (!token) {
    return null;
  }
  return parseClaims(token);
}

export function writeAccessToken(token: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (token) {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    }
    window.dispatchEvent(
      new CustomEvent(ACCESS_TOKEN_UPDATED_EVENT, {
        detail: { token },
      })
    );
  } catch {
    // ignore storage errors
  }
}

export function subscribeToAccessTokenChange(
  callback: (token: string | null, claims: AuthClaims | null) => void,
): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleCustom = (event: Event) => {
    const { token } = (event as CustomEvent<{ token?: string | null }>).detail ?? {};
    const claims = token ? parseClaims(token) : null;
    callback(token ?? null, claims);
  };

  const handleStorage = (event: StorageEvent) => {
    if (event.key === ACCESS_TOKEN_STORAGE_KEY) {
      const nextToken = event.newValue;
      callback(nextToken, nextToken ? parseClaims(nextToken) : null);
    }
  };

  window.addEventListener(ACCESS_TOKEN_UPDATED_EVENT, handleCustom as EventListener);
  window.addEventListener("storage", handleStorage);

  return () => {
    window.removeEventListener(ACCESS_TOKEN_UPDATED_EVENT, handleCustom as EventListener);
    window.removeEventListener("storage", handleStorage);
  };
}
