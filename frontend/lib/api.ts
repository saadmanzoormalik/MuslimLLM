export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

export type Citation = {
  title: string;
  author?: string;
  source_type: string;
  reference?: string;
  reliability_level: string;
  snippet: string;
  score?: number;
};

async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include", cache: "no-store" });
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    const refreshed = await fetch(`${API_BASE}/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshed.ok) return request(path, init, false);
  }
  return response;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await request(path);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await request(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await request(path, { method: "DELETE" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
