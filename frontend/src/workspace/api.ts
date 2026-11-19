const BASE = "/api/v1";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  key: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(path.startsWith(BASE) ? path : BASE + path, {
    ...init,
    headers: {
      ...(key ? { "X-API-Key": key } : {}),
      ...(init.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      /* Non-JSON proxy errors retain their HTTP status. */
    }
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}
export async function artifact(
  path: string,
  key: string,
  signal?: AbortSignal,
): Promise<Blob> {
  if (!/^\/api\/v1\/files\/[a-f0-9-]{36}\/[a-zA-Z0-9_.-]+$/.test(path))
    throw new Error("Invalid artifact location");
  const response = await fetch(path, {
    headers: key ? { "X-API-Key": key } : {},
    signal,
  });
  if (!response.ok)
    throw new ApiError(
      response.status,
      `Artifact unavailable (${response.status})`,
    );
  return response.blob();
}
