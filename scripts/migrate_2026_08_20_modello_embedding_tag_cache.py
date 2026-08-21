"""Migrazione live: colonna modello_embedding su tag_embedding_cache (v.
CLAUDE.md 2026-08-20 — tracciamento versione modello, per accorgersi se in
futuro Google cambia silenziosamente il comportamento di
gemini-embedding-001 e la cache finisce con vettori da spazi incompatibili
mescolati insieme). Nessun Alembic nel progetto — pattern ad-hoc già usato
per le migrazioni precedenti.

Uso: python scripts/migrate_2026_08_20_modello_embedding_tag_cache.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402
from services.text_embedding import MODELLO_EMBEDDING  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("1. Aggiungo colonna modello_embedding...")
    cur.execute("ALTER TABLE tag_embedding_cache ADD COLUMN IF NOT EXISTS modello_embedding VARCHAR(60)")

    print(f"2. Backfill righe esistenti con '{MODELLO_EMBEDDING}' (tutte calcolate finora con questo modello)...")
    cur.execute(
        "UPDATE tag_embedding_cache SET modello_embedding = %s WHERE modello_embedding IS NULL",
        (MODELLO_EMBEDDING,),
    )
    print(f"   {cur.rowcount} righe aggiornate.")

    print("3. Rendo la colonna NOT NULL (ora che tutte le righe sono valorizzate)...")
    cur.execute("ALTER TABLE tag_embedding_cache ALTER COLUMN modello_embedding SET NOT NULL")

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
