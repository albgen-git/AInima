"""Migrazione live: colonne inglesi per i contenuti generati dal sistema
mostrati direttamente all'utente (deroga a RNF-03, v. CLAUDE.md 2026-09-09
— segnalato dall'utente: pillole/analisi di coppia restavano in italiano
anche con interfaccia in inglese, testo misto IT/EN in Rubrica).

Aggiunge:
- pillole_libreria.titolo_en / testo_en
- matches.analisi_caratteriale_coppia_en
- personal_report.contenuto_report_en

Tutte NULL per le righe già esistenti (generate prima di questo fix) —
il fallback IT resta sempre disponibile lato applicativo.

Idempotente (ADD COLUMN IF NOT EXISTS).

Uso:
    python scripts/migrate_2026_09_09_contenuti_bilingue.py            (DB locale)
    python scripts/migrate_2026_09_09_contenuti_bilingue.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE pillole_libreria ADD COLUMN IF NOT EXISTS titolo_en VARCHAR(150);
ALTER TABLE pillole_libreria ADD COLUMN IF NOT EXISTS testo_en TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS analisi_caratteriale_coppia_en TEXT;
ALTER TABLE personal_report ADD COLUMN IF NOT EXISTS contenuto_report_en TEXT;
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
    print("Colonne _en per contenuti generati (pillole/analisi coppia/report personale) pronte.")
    conn.close()


if __name__ == "__main__":
    main()
