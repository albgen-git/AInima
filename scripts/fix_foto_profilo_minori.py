"""Rimuove le foto profilo che ritraggono minori (bug a monte nel generatore
GAN del DB Actor, mai filtrato per età — v. CLAUDE.md 2026-08-20). Stesso
identico problema già trovato e ripulito per foto_partner_ideale_url in una
sessione precedente, ma quella pulizia non copriva foto_profilo_url.

Metodo: centroide "volto infantile" ArcFace costruito sui 112 casi GIA'
confermati (le foto partner-ideale rimosse in precedenza — embedding
recuperati dalla cache .npy originale della pipeline di import, mai
cancellata anche se il DB era stato ripulito), applicato a
embeddings_cache.npy (foto profilo di tutti i 1000 attori). Zona alta
confidenza (>=0.40) verificata a campione (4 casi sparsi nel range,
tutti bambini inequivocabili) — rimossa in blocco, stesso trattamento già
validato per partner_ideale. Zona grigia (0.25-0.40) gestita a parte,
caso per caso con l'utente (risultato al campione: misto, ci sono falsi
positivi chiari) — non toccata da questo script.

Uso: python scripts/fix_foto_profilo_minori.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data_migration", "Actors DB", "Actors DB")
SOGLIA_ALTA_CONFIDENZA = 0.40


def cos_batch(mat, v):
    mat_n = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    return mat_n @ (v / np.linalg.norm(v))


def main():
    emb_profilo = np.load(os.path.join(BASE, "embeddings_cache.npy"))
    ids_profilo = np.load(os.path.join(BASE, "embeddings_ids.npy"))
    emb_pi = np.load(os.path.join(BASE, "pi_embeddings_cache.npy"))
    ids_pi = np.load(os.path.join(BASE, "pi_embeddings_ids.npy"))
    idx_pi = {int(a): i for i, a in enumerate(ids_pi)}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.source_actor_id FROM users u
        JOIN physical_profile p ON p.user_id = u.user_id
        WHERE u.source_actor_id IS NOT NULL AND p.foto_partner_ideale_url IS NULL
    """)
    confermati = cur.fetchall()
    emb_confermati = np.array([emb_pi[idx_pi[r["source_actor_id"]]] for r in confermati if r["source_actor_id"] in idx_pi])
    centroide = emb_confermati.mean(axis=0)
    print(f"Centroide costruito su {len(emb_confermati)} casi confermati.")

    sims = cos_batch(emb_profilo, centroide)
    cur.execute("SELECT user_id, source_actor_id FROM users WHERE source_actor_id IS NOT NULL")
    by_actor = {r["source_actor_id"]: r["user_id"] for r in cur.fetchall()}

    da_rimuovere = [
        by_actor[int(aid)] for i, aid in enumerate(ids_profilo)
        if int(aid) in by_actor and sims[i] >= SOGLIA_ALTA_CONFIDENZA
    ]
    print(f"Foto profilo in zona alta confidenza (>={SOGLIA_ALTA_CONFIDENZA}): {len(da_rimuovere)}")

    cur.execute("""
        UPDATE physical_profile SET foto_profilo_url = NULL, embedding_visivo_profilo = NULL
        WHERE user_id = ANY(%s::uuid[])
    """, ([str(u) for u in da_rimuovere],))
    print(f"Righe aggiornate: {cur.rowcount}")

    conn.commit()
    conn.close()
    print("Completato.")


if __name__ == "__main__":
    main()
