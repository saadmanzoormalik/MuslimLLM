export type AuthCallbackResult = {
  grantId?: string;
  state?: string;
  error?: string;
};

export interface ContextAuthPlatform {
  startAuthorization(url: string): Promise<void>;
  awaitCallback(): Promise<AuthCallbackResult>;
  secureStore(key: string, value: string): Promise<void>;
  secureDelete(key: string): Promise<void>;
}

export const browserContextAuthPlatform: ContextAuthPlatform = {
  async startAuthorization(url) {
    window.location.assign(url);
  },
  async awaitCallback() {
    const params = new URLSearchParams(window.location.search);
    return {
      grantId: params.get("grant_id") || undefined,
      state: params.get("state") || undefined,
      error: params.get("error") || undefined,
    };
  },
  async secureStore() {
    throw new Error("Browser JavaScript does not store provider credentials. Use the device secure store.");
  },
  async secureDelete() {
    return;
  },
};
