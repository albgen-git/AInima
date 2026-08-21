"""Migrazione live: nuova tabella tag_embedding_centroide (correzione
anisotropia sugli embedding dei tag, v. CLAUDE.md 2026-08-20). Nessun
Alembic nel progetto — pattern ad-hoc già usato per le migrazioni
precedenti.

Uso: python scripts/migrate_2026_08_20_centroide_tag_embedding.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402
from services import tag_matching  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("1. Nuova tabella tag_embedding_centroide...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tag_embedding_centroide (
            id                     SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            vettore                DOUBLE PRECISION[] NOT NULL,
            numero_tag_campione    INTEGER NOT NULL,
            calcolato_il           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    conn.commit()

    print("2. Calcolo il centroide dalla cache tag esistente...")
    riga = tag_matching.ricalcola_centroide(cur)
    conn.commit()
    conn.close()

    if riga is None:
        print("   cache tag_embedding_cache vuota — nessun centroide calcolato, verrà creato al primo tag disponibile.")
    else:
        print(f"   centroide calcolato su {riga['numero_tag_campione']} tag.")
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
