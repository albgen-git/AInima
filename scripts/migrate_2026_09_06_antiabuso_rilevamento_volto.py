"""Migrazione live: log persistente + anti-abuso sul rilevamento volto (RF-08c).

Richiesto esplicitamente dall'utente dopo un caso reale (foto "partner
ideale" di un piatto caricata con successo da un'utente reale, Danae) —
impossibile stabilire a posteriori se per un errore transitorio del
servizio AWS o altro, perché un fallimento di DetectFaces finiva solo in
un print() di console (v. CLAUDE.md). Due parti:

1. `rilevamento_volto_log` — traccia OGNI tentativo (non solo i
   fallimenti): 'Volto rilevato' | 'Nessun volto' | 'Errore servizio'.
2. `users.tentativi_falliti_rilevamento_volto` — contatore anti-abuso:
   dopo N tentativi CONSECUTIVI di "nessun volto" (system_config.
   tentativi_massimi_rilevamento_volto, default 3), l'account passa
   automaticamente a 'Sospeso' — evita che un attacco di upload ripetuti
   consumi indefinitamente le chiamate a pagamento di AWS Rekognition.
   Un errore del servizio stesso (non "nessun volto") non conta ai fini
   del contatore, non è colpa dell'utente.

Idempotente (ADD COLUMN/CREATE TABLE IF NOT EXISTS, INSERT ON CONFLICT).

Uso:
    python scripts/migrate_2026_09_06_antiabuso_rilevamento_volto.py            (DB locale)
    python scripts/migrate_2026_09_06_antiabuso_rilevamento_volto.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS tentativi_falliti_rilevamento_volto INT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS rilevamento_volto_log (
    log_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    tipo_immagine       VARCHAR(20) NOT NULL,
    esito                VARCHAR(20) NOT NULL,
    dettaglio_errore      TEXT,
    data_evento            TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO system_config (chiave, valore, descrizione) VALUES
    ('tentativi_massimi_rilevamento_volto', '3',
     'RF-08c: tentativi consecutivi di upload foto senza volto rilevato prima della sospensione automatica dell''account, anti-abuso (evita consumo eccessivo delle API AWS Rekognition)')
ON CONFLICT (chiave) DO NOTHING;
"""


def main():
    if "--render" in sys.argv:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        from db import get_conn  # noqa: E402

        conn = get_conn()

    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    print("tentativi_falliti_rilevamento_volto, rilevamento_volto_log, tentativi_massimi_rilevamento_volto: pronti.")
    conn.close()


if __name__ == "__main__":
    main()
