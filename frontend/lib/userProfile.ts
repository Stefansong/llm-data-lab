export const USER_ID_STORAGE_KEY = "llm-data-lab.user-id";
export const USER_ID_UPDATED_EVENT = "llm-data-lab:user-id-updated";

function normalizeUserId(value: unknown): number {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return 1;
  }
  return Math.floor(numeric);
}

export function readActiveUserId(): number {
  if (typeof window === "undefined") {
    return 1;
  }
  try {
    const raw = window.localStorage.getItem(USER_ID_STORAGE_KEY);
    if (!raw) {
      return 1;
    }
    return normalizeUserId(raw);
  } catch {
    return 1;
  }
}

export function writeActiveUserId(userId: number): number {
  if (typeof window === "undefined") {
    return 1;
  }
  const normalized = normalizeUserId(userId);
  try {
    window.localStorage.setItem(USER_ID_STORAGE_KEY, String(normalized));
    window.dispatchEvent(
      new CustomEvent(USER_ID_UPDATED_EVENT, {
        detail: { userId: normalized },
      })
    );
  } catch {
    // Ignore storage errors (private browsing, quota exceeded, etc.)
  }
  return normalized;
}

export function clearActiveUserId(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(USER_ID_STORAGE_KEY);
    window.dispatchEvent(
      new CustomEvent(USER_ID_UPDATED_EVENT, {
        detail: {},
      })
    );
  } catch {
    // ignore
  }
}

export function subscribeToUserIdChange(callback: (userId: number) => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleCustom = (event: Event) => {
    const customEvent = event as CustomEvent<{ userId?: number }>;
    const newValue = normalizeUserId(customEvent.detail?.userId ?? readActiveUserId());
    callback(newValue);
  };

  const handleStorage = (event: StorageEvent) => {
    if (event.key === USER_ID_STORAGE_KEY) {
      callback(readActiveUserId());
    }
  };

  window.addEventListener(USER_ID_UPDATED_EVENT, handleCustom as EventListener);
  window.addEventListener("storage", handleStorage);

  return () => {
    window.removeEventListener(USER_ID_UPDATED_EVENT, handleCustom as EventListener);
    window.removeEventListener("storage", handleStorage);
  };
}
