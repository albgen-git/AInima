"""Migrazione live: colonna flag_trappola_fallita su psychometric_scores
(Blocco B, v. CLAUDE.md — domande trappola condivise tra Big Five/
Attaccamento/EQ Score, Ainima_00_Indice_Schema_Consolidato_v1.md). Nessun
Alembic nel progetto — pattern ad-hoc già usato per le migrazioni precedenti.

Uso: python scripts/migrate_2026_08_21_flag_trappola_fallita.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("ALTER TABLE psychometric_scores ADD COLUMN IF NOT EXISTS flag_trappola_fallita SMALLINT NOT NULL DEFAULT 0")
    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
