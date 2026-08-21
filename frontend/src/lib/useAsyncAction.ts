import { useCallback, useState } from "react";

/** Hook condiviso per stato loading/errore su chiamate API — usato in tutta l'app.
 * Il messaggio mostrato viene sempre dall'errore reale (ApiError/NetworkError
 * hanno già un .message parlante, v. lib/api/client.ts) — mai un fallback
 * muto, altrimenti errori come "backend non raggiungibile" spariscono dietro
 * un generico "errore imprevisto" (successo reale solo con l'errore giusto
 * davanti: non indovinare, farlo dire al codice). */
export function useAsyncAction<Args extends unknown[], R>(
  action: (...args: Args) => Promise<R>
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (...args: Args): Promise<R | undefined> => {
      setLoading(true);
      setError(null);
      try {
        return await action(...args);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore imprevisto");
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [action]
  );

  return { run, loading, error, setError };
}
