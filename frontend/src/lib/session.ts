/**
 * Sessione: l'identità è lo user_id salvato in localStorage dopo la
 * verifica OTP (RF-02) — il backend emette anche un token JWT alla
 * verifica riuscita, salvato qui per prontezza futura, ma NON è ancora
 * richiesto/verificato su nessun'altra rotta dell'app (v. CLAUDE.md):
 * oggi conta ancora solo lo user_id, come nell'MVP precedente.
 */

const USER_ID_KEY = "ainima_user_id";
const TOKEN_KEY = "ainima_session_token";

export function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(USER_ID_KEY);
}

export function setUserId(userId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_ID_KEY, userId);
}

export function clearUserId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(USER_ID_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
}

export function setSessionToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}
