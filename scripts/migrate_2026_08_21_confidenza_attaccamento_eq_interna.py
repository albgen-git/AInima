"""Migrazione live: Blocco C, seconda passata (v. CLAUDE.md — correzioni di
specifica trovate durante l'implementazione: soglia irraggiungibile "< 0.6",
confidenza_dimensione mancante per l'Attaccamento, varianza interna EQ
mancante per Autoconsapevolezza/Responsabilità, bug di conteggio in
_ricalcola_confidenza_e_flag()). 4 nuove colonne su psychometric_scores +
bump a stable_v7 in matching_algorithm_versions.

Uso: python scripts/migrate_2026_08_21_confidenza_attaccamento_eq_interna.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

COLONNE = [
    "confidenza_attaccamento_ansia",
    "confidenza_attaccamento_evitamento",
    "confidenza_eq_autoregolazione_interna",
    "confidenza_eq_empatia_interna",
]


def main():
    conn = get_conn()
    cur = conn.cursor()

    for col in COLONNE:
        cur.execute(f"ALTER TABLE psychometric_scores ADD COLUMN IF NOT EXISTS {col} REAL NOT NULL DEFAULT 1.0")
    print(f"{len(COLONNE)} colonne aggiunte/verificate.")

    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v7', 'Blocco C, seconda passata (v. CLAUDE.md — correzioni di specifica trovate durante l''implementazione, non solo di codice): (a) aggiunta confidenza_dimensione per Attaccamento, mancante del tutto (Ainima_Test_Attaccamento_v1.md §5 Step 3bis); (b) aggiunto il controllo di varianza interna per tutti e 4 i pilastri EQ (Ainima_Test_EQScore_v1.md §4a) — prima Autoconsapevolezza/Responsabilità non avevano alcun controllo qualità; per Autoregolazione/Empatia il valore pubblico finale è min(interno, incrociato col Big Five), mai una sostituzione diretta; (c) _ricalcola_confidenza_e_flag() riscritta per costruire esplicitamente l''insieme deduplicato di 11 confidenze (5 Big Five + 4 EQ + 2 Attaccamento) e contare quante sono == 0.6, invece di un contatore incrementato una volta per ogni controllo incrociato fallito (bug: due controlli diversi sulla stessa dimensione Autoregolazione gonfiavano il conteggio come se fossero 2 dimensioni anomale invece di 1) — formula autorevole in Ainima_Algoritmo_Ranking_Finale_v1.md, "Soglia per revisione umana". Cambia chi viene escluso dal matching (flag_profilo_per_revisione_dati è un filtro hard in matching_engine.py), non solo bookkeeping.')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
