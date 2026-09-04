"""Migrazione live: aggiunge email_inviata_log.provider_message_id (v.
CLAUDE.md — trovato dal vivo il 2026-09-04, un utente reale segnalava
mancata ricezione di una email di engagement e non c'era alcun id
tracciato per verificarne lo stato lato provider). Nullable, idempotente.

Uso:
    python scripts/migrate_2026_09_04_provider_message_id.py            (DB locale)
    python scripts/migrate_2026_09_04_provider_message_id.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = "ALTER TABLE email_inviata_log ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(255);"


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
    print("email_inviata_log.provider_message_id aggiunta (o già presente).")
    conn.close()


if __name__ == "__main__":
    main()
