"""
simulate_matching_narrativo.py
Ciclo di abbinamento (stable matching) ristretto ai soli profili che hanno
già l'embedding narrativo reale (self_embedding_vector/ideal_embedding_vector
popolati da run_narrative_pipeline.py) — per vedere concretamente quanto la
Coerenza Narrativa (STEP 3) pesa nel FINAL_SCORE rispetto agli altri 3
componenti, ora che non è più un placeholder neutro 0.5 per questo
sottoinsieme.

Non scrive nulla su matches — è solo un'anteprima diagnostica.

Uso: python simulate_matching_narrativo.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402
from services import matching_engine as me  # noqa: E402


def main():
    conn = get_conn()
    cur = conn.cursor()

    pool_completo = me.load_pool(cur)
    cfg = me.load_config_floats(cur)

    cur.execute("SELECT user_id FROM psychometric_scores WHERE self_embedding_vector IS NOT NULL")
    id_pronti = {r["user_id"] for r in cur.fetchall()}
    pool = {uid: dati for uid, dati in pool_completo.items() if uid in id_pronti}
    print(f"Pool ristretto: {len(pool)} profili con embedding narrativo reale (su {len(pool_completo)} Attivi totali)")

    history_pairs = set()  # non rilevante per questa anteprima diagnostica
    gia_impegnati = set()

    preference_lists = {}
    motivi_vuoti = {}
    for seeker_id in pool:
        lista, motivo, _ = me.build_preference_list(seeker_id, pool, cfg, history_pairs, gia_impegnati)
        if lista:
            preference_lists[seeker_id] = lista
        elif motivo:
            motivi_vuoti[seeker_id] = motivo

    coppie = me.stable_match(preference_lists)
    n_coppie_uniche = len({frozenset((a, b)) for a, b in coppie.items()})
    print(f"Coppie proposte: {n_coppie_uniche} — senza candidati/sotto soglia: {len(motivi_vuoti)} — non abbinati: {len(pool) - len(coppie) - len(motivi_vuoti)}")
    print()

    scritti = set()
    righe = []
    for uid, cand_id in coppie.items():
        chiave = frozenset((uid, cand_id))
        if chiave in scritti:
            continue
        scritti.add(chiave)

        a, b = pool[uid], pool[cand_id]
        bf = me.bigfive_score(a, b)
        eq = me.eq_score(a, b)
        narrativa = me.coerenza_narrativa_score(a, b)
        dist = me.haversine_km(a["lon"], a["lat"], b["lon"], b["lat"])
        _, punteggio_distanza = me.valuta_distanza(a, b, dist, cfg)
        soft = me.combina_soft_e_distanza(a, b, punteggio_distanza)
        final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                 cfg["weight_narrativa"] * narrativa + cfg["weight_preferenze_soft"] * soft)

        contributo_narrativa = cfg["weight_narrativa"] * narrativa
        righe.append((a["nome"], b["nome"], final, bf, eq, narrativa, soft, contributo_narrativa))

    righe.sort(key=lambda r: -r[2])
    print(f"{'Coppia':30s} {'FINAL':>7s} {'BigFive':>8s} {'EQ/Att':>8s} {'Narrat.':>8s} {'Soft':>7s}  {'contrib.narr.'}")
    for nome_a, nome_b, final, bf, eq, narrativa, soft, contrib in righe:
        coppia = f"{nome_a} <-> {nome_b}"
        print(f"{coppia:30s} {final:7.3f} {bf:8.3f} {eq:8.3f} {narrativa:8.3f} {soft:7.3f}  {contrib:.3f} ({contrib/final*100:.0f}% del FINAL_SCORE)")

    if righe:
        narrativa_vals = [r[5] for r in righe]
        print()
        print(f"Coerenza narrativa sulle coppie proposte: min={min(narrativa_vals):.3f} max={max(narrativa_vals):.3f} "
              f"media={sum(narrativa_vals)/len(narrativa_vals):.3f}")

    conn.close()


if __name__ == "__main__":
    main()
