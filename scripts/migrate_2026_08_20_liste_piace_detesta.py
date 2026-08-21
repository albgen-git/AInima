"""Migrazione live per il punto 5 (Ainima_Liste_Piace_Detesta_v1.md):
nuova tabella interest_tags (4 liste grezze + 4 array di tag) e cache
condivisa tag_embedding_cache. Nessun Alembic nel progetto — pattern
ad-hoc già usato per le migrazioni precedenti.

Uso: python scripts/migrate_2026_08_20_liste_piace_detesta.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("1. Nuova tabella interest_tags...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interest_tags (
            user_id                   UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            mi_piace                  TEXT,
            non_sopporto               TEXT,
            partner_vorrei              TEXT,
            partner_non_vorrei           TEXT,
            mi_piace_tags                TEXT[],
            non_sopporto_tags             TEXT[],
            partner_vorrei_tags            TEXT[],
            partner_non_vorrei_tags         TEXT[],
            data_ultima_modifica              TIMESTAMPTZ
        )
    """)

    print("2. Nuova tabella tag_embedding_cache...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tag_embedding_cache (
            tag_normalizzato       VARCHAR(120) PRIMARY KEY,
            embedding_vector         DOUBLE PRECISION[] NOT NULL,
            prima_volta_vista_il        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    print("3. Righe vuote in interest_tags per gli utenti esistenti (stesso pattern delle altre tabelle satellite)...")
    cur.execute("""
        INSERT INTO interest_tags (user_id)
        SELECT user_id FROM users
        WHERE user_id NOT IN (SELECT user_id FROM interest_tags)
    """)

    print("4. matching_algorithm_versions: aggiungo stable_v4...")
    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v4', 'Aggiunta Punteggio_Tag_Liste (Ainima_Liste_Piace_Detesta_v1.md) dentro lo STEP 4 — Preferenze Soft: confronto a similarità vettoriale per singolo tag tra le liste mi_piace/non_sopporto/partner_vorrei/partner_non_vorrei di due candidati, con penalità dedicata sui rifiuti espliciti. Cache di embedding condivisa tra tutti gli utenti per tag.')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
