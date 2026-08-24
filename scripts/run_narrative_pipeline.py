"""
run_narrative_pipeline.py
Esegue la pipeline REALE (Prompt 3a/3b + embedding Gemini) sui campi liberi
già generati da generate_narrative_data.py, per i profili di test che non
hanno ancora self_embedding_vector/ideal_embedding_vector — così
matching_engine.coerenza_narrativa_score smette di usare il fallback
neutro 0.5 e riflette davvero il contenuto dei testi.

Idempotente/riprendibile: seleziona solo chi ha ancora self_embedding_vector
NULL, quindi si può lanciare più volte con --limit crescenti senza rifare
lavoro già fatto (e senza ripagare le chiamate già effettuate).

Uso: python run_narrative_pipeline.py [--limit N]
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402
from routers.psychometric import GENERAZIONE_PROFILO_CANONICO_ATTIVA  # noqa: E402
from services import llm_pipeline, text_embedding  # noqa: E402


def main():
    # v. CLAUDE.md — stesso flag di routers/psychometric.py: Prompt 5 (il
    # generatore del report che dovrebbe consumare questo output) non è mai
    # stato implementato, quindi questo script pagherebbe chiamate LLM/
    # embedding reali per colonne che nessun codice rilegge. In pausa
    # insieme all'endpoint /narrative, stesso interruttore.
    if not GENERAZIONE_PROFILO_CANONICO_ATTIVA:
        print("GENERAZIONE_PROFILO_CANONICO_ATTIVA è False (v. CLAUDE.md) — "
              "script in pausa, nessuna chiamata LLM/embedding effettuata.")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.source_actor_id, pn.descrizione_di_se, pn.descrizione_partner_ideale
        FROM users u
        JOIN profile_narrative pn ON pn.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        WHERE u.source_actor_id IS NOT NULL
          AND pn.descrizione_di_se IS NOT NULL AND pn.descrizione_partner_ideale IS NOT NULL
          AND ps.self_embedding_vector IS NULL
        ORDER BY u.source_actor_id
        LIMIT %s
    """, (args.limit,))
    rows = cur.fetchall()
    print(f"Profili da processare in questo batch: {len(rows)}")

    ok, falliti = 0, 0
    inizio = time.time()
    for i, r in enumerate(rows, 1):
        uid = str(r["user_id"])
        try:
            self_canonico = llm_pipeline.estrai_profilo_self(r["descrizione_di_se"])
            self_emb = text_embedding.embed_testo(self_canonico)
            ideale_canonico = llm_pipeline.estrai_profilo_ideale(r["descrizione_partner_ideale"])
            ideale_emb = text_embedding.embed_testo(ideale_canonico)

            cur.execute("""
                UPDATE psychometric_scores SET
                    self_profile_canonico = %s, self_embedding_vector = %s,
                    ideal_partner_profile_canonico = %s, ideal_embedding_vector = %s
                WHERE user_id = %s
            """, (self_canonico, self_emb, ideale_canonico, ideale_emb, uid))
            conn.commit()
            ok += 1
        except Exception as e:
            conn.rollback()
            falliti += 1
            print(f"  [ERRORE] actor {r['source_actor_id']} ({uid}): {e}")

        if i % 10 == 0 or i == len(rows):
            trascorsi = time.time() - inizio
            print(f"  {i}/{len(rows)} processati ({ok} ok, {falliti} falliti) — {trascorsi:.0f}s")

    conn.close()
    print(f"Completato: {ok} riusciti, {falliti} falliti su {len(rows)}.")


if __name__ == "__main__":
    main()
