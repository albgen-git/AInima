"""Migrazione live: Blocco D (v. CLAUDE.md — Ainima_Test_Profilo_Relazionale_v1.md).
8 colonne JSONB su psychometric_scores (Test Profilo Relazionale) + 2 colonne
BOOLEAN su matches (flag_rifiuto_esplicito/flag_asimmetria_narrativa,
persistiti al momento della creazione del match) + bump a stable_v8 in
matching_algorithm_versions.

Uso: python scripts/migrate_2026_08_21_profilo_relazionale.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

COLONNE_PSYCHOMETRIC = [
    "profilo_valori_self", "profilo_valori_partner_ideale",
    "profilo_stile_vita_self", "profilo_stile_vita_partner_ideale",
    "profilo_dinamica_relazionale_self", "profilo_dinamica_relazionale_partner_ideale",
    "profilo_aspirazioni_self", "profilo_aspirazioni_partner_ideale",
]

COLONNE_MATCHES = ["flag_rifiuto_esplicito", "flag_asimmetria_narrativa"]


def main():
    conn = get_conn()
    cur = conn.cursor()

    for col in COLONNE_PSYCHOMETRIC:
        cur.execute(f"ALTER TABLE psychometric_scores ADD COLUMN IF NOT EXISTS {col} JSONB")
    print(f"{len(COLONNE_PSYCHOMETRIC)} colonne JSONB aggiunte/verificate su psychometric_scores.")

    for col in COLONNE_MATCHES:
        cur.execute(f"ALTER TABLE matches ADD COLUMN IF NOT EXISTS {col} BOOLEAN NOT NULL DEFAULT FALSE")
    print(f"{len(COLONNE_MATCHES)} colonne BOOLEAN aggiunte/verificate su matches.")

    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v8', 'Blocco D (v. CLAUDE.md, Ainima_Test_Profilo_Relazionale_v1.md): STEP 3 (Coerenza Narrativa) non usa più il confronto a embedding tra i campi liberi (self_embedding_vector/ideal_embedding_vector, Judge LLM già rimosso in stable_v3) — sostituito da matching_engine.punteggio_narrativo_strutturato(), aritmetica diretta su 13 sotto-dimensioni chiuse (Valori/Stile di Vita/Dinamica Relazionale/Aspirazioni, self vs partner ideale, 26 item). Aggiunto flag_asimmetria_narrativa (scarto >0.5 tra le due direzioni su una sotto-dimensione) con lo stesso trattamento di flag_rifiuto_esplicito, entrambi ora persistiti su matches al momento della creazione (colonne dedicate, mai ricalcolati a posteriori) ed esposti in GET /admin/matches/{id}/why (dato grezzo, uso interno) — GET /users/{id}/proposal/analysis (rivolto all''utente) li riformula invece in un unico spunto costruttivo, mai un''etichetta cruda. Il Test Profilo Relazionale entra nel gate di attivazione RF-09 (decisione esplicita dell''utente: pesa 0.20 in FINAL_SCORE, categoria "componente obbligatoria" non "opzionale").')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
