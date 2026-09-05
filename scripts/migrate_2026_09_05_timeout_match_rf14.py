"""Migrazione live: timeout match (RF-14/14b/14c/14d, §7.6 — v. CLAUDE.md).

Aggiunge `matches.notifica_scadenza_inviata` (bool, default false) — usata
da services/match_timeout.py per evitare invii duplicati dell'email di
scadenza se il processo schedulato gira più volte sullo stesso match
prima che l'invio sia confermato riuscito.

Nessuna migrazione di enum necessaria: 'Scaduto' esisteva già in
stato_match_enum da prima (dichiarato ma mai scritto da nessun codice —
gap segnalato dall'utente, ora colmato).

Idempotente (ALTER ... ADD COLUMN IF NOT EXISTS).

Uso:
    python scripts/migrate_2026_09_05_timeout_match_rf14.py            (DB locale)
    python scripts/migrate_2026_09_05_timeout_match_rf14.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


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
    cur.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS notifica_scadenza_inviata BOOLEAN NOT NULL DEFAULT FALSE")
    conn.commit()

    cur.execute("SELECT count(*) AS n FROM matches")
    print(f"Colonna notifica_scadenza_inviata pronta su {cur.fetchone()['n']} match esistenti (tutti FALSE di default).")
    conn.close()


if __name__ == "__main__":
    main()
