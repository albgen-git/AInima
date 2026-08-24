"""Migrazione live: 9 colonne confidenza_dimensione su psychometric_scores
(Blocco C, v. CLAUDE.md — Ainima_Test_Psicometrico_BigFive_v1.md §7 Step 4,
Ainima_Test_EQScore_v1.md §4) + bump a stable_v6 in matching_algorithm_versions.
Nessun Alembic nel progetto — pattern ad-hoc già usato per le migrazioni
precedenti.

Uso: python scripts/migrate_2026_08_21_confidenza_dimensione.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

COLONNE = [
    "confidenza_big5_estroversione", "confidenza_big5_gradevolezza",
    "confidenza_big5_coscienziosita", "confidenza_big5_nevroticismo",
    "confidenza_big5_apertura",
    "confidenza_eq_autoconsapevolezza", "confidenza_eq_autoregolazione",
    "confidenza_eq_empatia", "confidenza_eq_responsabilita",
]


def main():
    conn = get_conn()
    cur = conn.cursor()

    for col in COLONNE:
        cur.execute(f"ALTER TABLE psychometric_scores ADD COLUMN IF NOT EXISTS {col} REAL NOT NULL DEFAULT 1.0")
    print(f"{len(COLONNE)} colonne aggiunte/verificate.")

    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v6', 'Blocco C: introdotta confidenza_dimensione — un profilo con varianza interna anomala su una dimensione Big Five, o con un''incoerenza statistica Big Five/EQ, pesa meno quella dimensione/pilastro nel calcolo finale (moltiplicatore 0.6). matching_engine.bigfive_score() ora usa una media pesata sulla confidenza minima tra i due profili; score_maturita_emotiva ricalcolato alla fonte con pesi EQ corretti dalla confidenza.')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
