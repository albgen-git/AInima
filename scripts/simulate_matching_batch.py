"""
simulate_matching_batch.py
Esegue la pipeline di matching (STEP 0-4 + tie-break, v. simulate_matching.py)
per TUTTI gli utenti attivi del pool, non solo un campione — per avere
statistiche aggregate su come si comporta l'algoritmo su scala.

Non genera nessuna proposta reale né scrive nulla nel DB: è una simulazione
di sola lettura, un ciclo mensile "a freddo" su tutto il pool.

Uso: python simulate_matching_batch.py
"""

import os
import statistics
import time

import psycopg2
from dotenv import load_dotenv

from simulate_matching import (
    load_pool, load_config, hard_filters_ok, haversine_km,
    bigfive_score, eq_score, soft_score, cosine, SOGLIA_SIMILARITA_MINIMA,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))


def media_bidirezionale(seeker, cand):
    sims = []
    if seeker["emb_pi"] is not None and cand["emb_profilo"] is not None:
        sims.append(cosine(seeker["emb_pi"], cand["emb_profilo"]))
    if cand["emb_pi"] is not None and seeker["emb_profilo"] is not None:
        sims.append(cosine(cand["emb_pi"], seeker["emb_profilo"]))
    if not sims:
        return None
    return sum(sims) / len(sims)


def run_one(seeker_id, pool, cfg):
    seeker = pool[seeker_id]
    if seeker["red_flags"]:
        return {"esito": "revisione_umana"}

    candidati = []
    for cand_id, cand in pool.items():
        if cand_id == seeker_id:
            continue
        dist = haversine_km(seeker["lon"], seeker["lat"], cand["lon"], cand["lat"])
        ok, _ = hard_filters_ok(seeker, cand, dist)
        if not ok:
            continue
        bf = bigfive_score(seeker, cand)
        eq = eq_score(seeker, cand)
        soft = (soft_score(seeker, cand) + soft_score(cand, seeker)) / 2
        final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                 cfg["weight_narrativa"] * 0.5 + cfg["weight_preferenze_soft"] * soft)
        candidati.append({"id": cand_id, "cand": cand, "final": final})

    pool_size = len(candidati)
    if not candidati:
        return {"esito": "nessun_candidato", "pool_size": 0}

    candidati.sort(key=lambda c: c["final"], reverse=True)
    migliore = candidati[0]

    if migliore["final"] < cfg["soglia_minima_proposta"]:
        return {"esito": "slow_matching", "pool_size": pool_size, "top_score": migliore["final"]}

    soglia_tb = cfg["soglia_tie_break_visivo"]
    pari_merito = [c for c in candidati if migliore["final"] - c["final"] <= soglia_tb]
    tie_break_usato = False
    vincitore = migliore

    if len(pari_merito) > 1:
        medie = {id(c): media_bidirezionale(seeker, c["cand"]) for c in pari_merito}
        migliore_media = max((m for m in medie.values() if m is not None), default=None)
        if migliore_media is not None and migliore_media >= SOGLIA_SIMILARITA_MINIMA:
            pari_merito.sort(key=lambda c: medie[id(c)] if medie[id(c)] is not None else -1, reverse=True)
            vincitore = pari_merito[0]
            tie_break_usato = True

    return {
        "esito": "proposta",
        "pool_size": pool_size,
        "gruppo_pari_merito": len(pari_merito),
        "tie_break_usato": tie_break_usato,
        "final_score": vincitore["final"],
    }


def main():
    conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
    )
    cur = conn.cursor()
    pool = load_pool(cur)
    cfg = load_config(cur)
    print(f"Pool caricato: {len(pool)} utenti attivi.")

    t0 = time.time()
    risultati = []
    for i, seeker_id in enumerate(pool.keys(), 1):
        risultati.append(run_one(seeker_id, pool, cfg))
        if i % 100 == 0:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(pool) - i)
            print(f"  {i}/{len(pool)} ... ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\nCompletato in {elapsed:.1f}s ({elapsed/len(pool)*1000:.1f}ms/utente)")

    # ── statistiche aggregate ─────────────────────────────────────────────
    conteggi = {}
    for r in risultati:
        conteggi[r["esito"]] = conteggi.get(r["esito"], 0) + 1

    n = len(risultati)
    print(f"\n=== ESITI SU {n} UTENTI ===")
    for esito, count in sorted(conteggi.items(), key=lambda x: -x[1]):
        print(f"  {esito:20s}: {count:4d}  ({count/n*100:.1f}%)")

    proposte = [r for r in risultati if r["esito"] == "proposta"]
    if proposte:
        scores = [r["final_score"] for r in proposte]
        pool_sizes = [r["pool_size"] for r in proposte]
        tie_breaks_usati = sum(1 for r in proposte if r["tie_break_usato"])
        gruppi_pari_merito = [r["gruppo_pari_merito"] for r in proposte]

        print(f"\n=== TRA CHI RICEVE UNA PROPOSTA ({len(proposte)} utenti) ===")
        print(f"  FINAL_SCORE: media={statistics.mean(scores):.3f}  mediana={statistics.median(scores):.3f}  "
              f"min={min(scores):.3f}  max={max(scores):.3f}  dev.std={statistics.stdev(scores):.3f}")
        print(f"  Dimensione pool dopo filtri hard: media={statistics.mean(pool_sizes):.1f}  "
              f"mediana={statistics.median(pool_sizes):.0f}  min={min(pool_sizes)}  max={max(pool_sizes)}")
        print(f"  Gruppo pari merito (entro soglia_tie_break_visivo): media={statistics.mean(gruppi_pari_merito):.1f}")
        print(f"  Tie-break visivo attivato: {tie_breaks_usati}/{len(proposte)} ({tie_breaks_usati/len(proposte)*100:.1f}%)")

    slow = [r for r in risultati if r["esito"] == "slow_matching"]
    if slow:
        top_scores = [r["top_score"] for r in slow]
        print(f"\n=== SLOW MATCHING (sotto soglia, {len(slow)} utenti) ===")
        print(f"  Miglior punteggio comunque raggiunto: media={statistics.mean(top_scores):.3f}  "
              f"max={max(top_scores):.3f} (soglia richiesta: {cfg['soglia_minima_proposta']})")

    nessun_cand = [r for r in risultati if r["esito"] == "nessun_candidato"]
    revisione = [r for r in risultati if r["esito"] == "revisione_umana"]
    print(f"\n=== ALTRO ===")
    print(f"  Nessun candidato sopravvive ai filtri hard: {len(nessun_cand)}")
    print(f"  Esclusi per red flag (revisione umana prioritaria): {len(revisione)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
