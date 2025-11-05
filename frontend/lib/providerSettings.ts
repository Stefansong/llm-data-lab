import { getProviderCredentials, updateProviderCredentials } from "@/lib/api";

export const PROVIDER_CREDENTIALS_UPDATED_EVENT = "provider-credentials-updated";

export type ProviderCredential = {
  apiKey?: string;
  baseUrl?: string;
  defaultModels?: string[];
};

export type ProviderCredentialMap = Record<string, ProviderCredential>;

let cachedCredentials: ProviderCredentialMap | null = null;

export async function fetchProviderCredentials(force = false): Promise<ProviderCredentialMap> {
  if (!cachedCredentials || force) {
    cachedCredentials = await getProviderCredentials();
  }
  return JSON.parse(JSON.stringify(cachedCredentials ?? {}));
}

export async function saveProviderCredentials(
  data: ProviderCredentialMap
): Promise<ProviderCredentialMap> {
  cachedCredentials = await updateProviderCredentials(data);
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent(PROVIDER_CREDENTIALS_UPDATED_EVENT, { detail: cachedCredentials })
    );
  }
  return JSON.parse(JSON.stringify(cachedCredentials ?? {}));
}
