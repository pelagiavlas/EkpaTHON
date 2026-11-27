// Small wrapper around fetch. Errors carry a message that can be shown as is.

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

const OFFLINE = "Δεν βρίσκω την εφαρμογή στον υπολογιστή. Έλεγξε ότι τρέχει ο server και δοκίμασε ξανά.";
const GENERIC = "Κάτι δεν πήγε καλά. Δοκίμασε ξανά.";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    const isForm = body instanceof FormData;
    response = await fetch(`/api${path}`, {
      method,
      headers: body && !isForm ? { "Content-Type": "application/json" } : undefined,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(OFFLINE, 0);
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new ApiError(typeof detail === "string" ? detail : GENERIC, response.status);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  del: (path: string) => request<void>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
};

export function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC;
}
