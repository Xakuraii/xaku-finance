/**
 * HTTP API client for XakuFinance.
 * Keeps access token in memory, performs automatic single refresh on 401,
 * and normalizes error responses into typed API errors.
 */

export interface ApiErrorPayload {
  code: string;
  message: string;
  field?: string | null;
  details?: Record<string, unknown>;
}

export class ApiError extends Error {
  code: string;
  status: number;
  field?: string | null;
  details: Record<string, unknown>;
  requestId?: string;

  constructor(status: number, payload: ApiErrorPayload, requestId?: string) {
    super(payload.message || `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.code || "unknown_error";
    this.field = payload.field;
    this.details = payload.details || {};
    this.requestId = requestId;
  }
}

let accessToken: string | null = null;
let isRefreshing = false;
let refreshSubscribers: ((token: string | null) => void)[] = [];

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

async function tryRefreshToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/v1/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });

    if (!res.ok) {
      setAccessToken(null);
      return null;
    }

    const data = await res.json();
    const newToken = data.access || null;
    setAccessToken(newToken);
    return newToken;
  } catch {
    setAccessToken(null);
    return null;
  }
}

export interface RequestOptions extends RequestInit {
  idempotencyKey?: string;
}

export async function request<T = unknown>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  if (options.idempotencyKey) {
    headers.set("Idempotency-Key", options.idempotencyKey);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  // Handle 401 refresh once
  if (response.status === 401 && !url.includes("/auth/")) {
    if (!isRefreshing) {
      isRefreshing = true;
      const newToken = await tryRefreshToken();
      isRefreshing = false;
      onRefreshed(newToken);

      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
        const retryRes = await fetch(url, { ...options, headers, credentials: "include" });
        return handleResponse<T>(retryRes);
      }
    } else {
      // Wait for existing refresh to resolve
      return new Promise<T>((resolve, reject) => {
        refreshSubscribers.push(async (newToken) => {
          if (!newToken) {
            reject(new ApiError(401, { code: "not_authenticated", message: "Session expired" }));
            return;
          }
          headers.set("Authorization", `Bearer ${newToken}`);
          try {
            const retryRes = await fetch(url, { ...options, headers, credentials: "include" });
            resolve(await handleResponse<T>(retryRes));
          } catch (err) {
            reject(err);
          }
        });
      });
    }
  }

  return handleResponse<T>(response);
}

async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get("content-type");
  const isJson = contentType && contentType.includes("application/json");

  if (!res.ok) {
    let errorPayload: ApiErrorPayload = {
      code: "request_failed",
      message: res.statusText || "Request failed",
    };
    let requestId: string | undefined;

    if (isJson) {
      try {
        const body = await res.json();
        if (body.error) {
          errorPayload = body.error;
          requestId = body.request_id;
        } else if (body.detail) {
          errorPayload = { code: "error", message: String(body.detail) };
        }
      } catch {
        // ignore JSON parse failure
      }
    }
    throw new ApiError(res.status, errorPayload, requestId);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return isJson ? (await res.json()) : (({} as unknown) as T);
}

export const api = {
  get: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "GET" }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(url: string, options?: RequestOptions) =>
    request<T>(url, { ...options, method: "DELETE" }),
};
