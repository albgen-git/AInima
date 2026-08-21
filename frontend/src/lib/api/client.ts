const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE_URL && typeof window !== "undefined") {
  console.error(
    "NEXT_PUBLIC_API_BASE_URL non impostata — controlla .env.local"
  );
}

/** Messaggio leggibile a partire dal campo "detail" di una risposta FastAPI:
 * una stringa (HTTPException classica) o la lista di errori di validazione
 * Pydantic ({"loc", "msg", "type"}[]) restituita sui 422. */
function messaggioDaDetail(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const primo = detail[0];
    if (primo && typeof primo === "object" && "msg" in primo) {
      const campo = Array.isArray(primo.loc) ? primo.loc.at(-1) : undefined;
      return campo ? `${campo}: ${primo.msg}` : String(primo.msg);
    }
  }
  return `Richiesta fallita con stato ${status}`;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(messaggioDaDetail(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Il fetch stesso è fallito (server irraggiungibile, CORS, rete assente) —
 * distinto da ApiError, che invece è una risposta HTTP ricevuta ma di errore. */
export class NetworkError extends Error {
  constructor(cause: unknown) {
    super(
      "Impossibile contattare il server. Verifica che il backend sia in esecuzione e riprova."
    );
    this.name = "NetworkError";
    this.cause = cause;
  }
}

async function parseErrorDetail(res: Response): Promise<unknown> {
  try {
    const body = await res.json();
    return body?.detail ?? body;
  } catch {
    return res.statusText;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch (err) {
    throw new NetworkError(err);
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorDetail(res));
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData }),
};

/** URL assoluto per risorse servite come file (foto, vCard, ecc.), non come fetch JSON. */
export function apiAssetUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export { API_BASE_URL };
