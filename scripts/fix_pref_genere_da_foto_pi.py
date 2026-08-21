"""
fix_pref_genere_da_foto_pi.py
Corregge dealbreaker_criteria.pref_genere_cercato usando il genere
percepito dalla foto "partner ideale" caricata, invece del valore
casuale ereditato dall'id_orientamento del DB Actor (che il generatore
originale non collegava mai alla foto scaricata — v. bug in
generate_pi.py: pi_gender_tag() calcolato ma mai usato per filtrare
il download da thispersondoesnotexist.com).

Metodo: nearest-centroid sugli embedding ArcFace già presenti in
physical_profile (nessuna nuova dipendenza/installazione).
  1. Centroide_M = media embedding_visivo_profilo di chi è Maschile
     Centroide_F = media embedding_visivo_profilo di chi è Femminile
  2. Per ogni foto_partner_ideale: genere_percepito = M o F, quello
     dei due centroidi con cosine similarity più alta.
  3. CONFIDENZA: applica la correzione solo se il margine tra le due
     similarità è >= SOGLIA_MARGINE (validata a mano su ~20 casi
     campione: sotto 0.05 il metodo può sbagliare — v. caso Amina
     Fontana, margine 0.048, classificata Maschile ma foto di donna).
     Sotto soglia, ripristina il valore originale (RNG deterministico
     sullo stesso seed di generate_synthetic_data.py) invece di
     tenere una correzione inaffidabile.

Utenti con genere 'Non binario'/'Altro': esclusi dalla correzione.

Uso: python fix_pref_genere_da_foto_pi.py
"""

import os
import random
import numpy as np
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

SOGLIA_MARGINE = 0.05


def cosine(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def pref_genere_originale(genere: str, orientamento: str, actor_id: int) -> str:
    """Ricalcola il valore originale generato da generate_synthetic_data.py
    (stesso seed = actor_id * 7919), per poter ripristinare i casi a bassa
    confidenza invece di lasciare una correzione inaffidabile."""
    rng = random.Random(actor_id * 7919)
    if orientamento == "Eterosessuale":
        if genere == "Maschile":
            return "Femminile"
        if genere == "Femminile":
            return "Maschile"
        return rng.choice(["Maschile", "Femminile"])
    if orientamento == "Omosessuale":
        if genere in ("Maschile", "Femminile"):
            return genere
        return rng.choice(["Maschile", "Femminile"])
    return rng.choice(["Maschile", "Femminile", "Non binario", "Altro"])


def main():
    conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.genere, u.orientamento_sessuale, u.source_actor_id,
               p.embedding_visivo_profilo, p.embedding_visivo_partner_ideale
        FROM users u JOIN physical_profile p ON p.user_id = u.user_id
        WHERE p.embedding_visivo_profilo IS NOT NULL
    """)
    rows = cur.fetchall()

    emb_m = [e for _, g, _, _, e, _ in rows if g == "Maschile"]
    emb_f = [e for _, g, _, _, e, _ in rows if g == "Femminile"]
    centroide_m = np.mean(np.array(emb_m), axis=0)
    centroide_f = np.mean(np.array(emb_f), axis=0)
    print(f"Centroidi costruiti su {len(emb_m)} profili M e {len(emb_f)} profili F.")

    corretti = 0
    ripristinati = 0
    saltati_genere_non_binario = 0
    saltati_no_foto_pi = 0

    for uid, genere, orientamento, actor_id, emb_profilo, emb_pi in rows:
        if genere not in ("Maschile", "Femminile"):
            saltati_genere_non_binario += 1
            continue
        if emb_pi is None:  # foto rimossa nel controllo minori, o mai caricata
            saltati_no_foto_pi += 1
            continue

        sim_m = cosine(emb_pi, centroide_m)
        sim_f = cosine(emb_pi, centroide_f)
        margine = abs(sim_m - sim_f)

        if margine >= SOGLIA_MARGINE:
            genere_percepito = "Maschile" if sim_m > sim_f else "Femminile"
            nuovo_pref = genere if genere_percepito == genere else genere_percepito
            corretti += 1
        else:
            nuovo_pref = pref_genere_originale(genere, orientamento, actor_id)
            ripristinati += 1

        cur.execute(
            "UPDATE dealbreaker_criteria SET pref_genere_cercato = %s WHERE user_id = %s",
            (nuovo_pref, str(uid)),
        )

    conn.commit()
    print(f"Corretti con alta confidenza (margine >= {SOGLIA_MARGINE}): {corretti}")
    print(f"Ripristinati al valore originale (margine < {SOGLIA_MARGINE}, confidenza insufficiente): {ripristinati}")
    print(f"Saltati (genere non binario/altro): {saltati_genere_non_binario}")
    print(f"Saltati (senza foto partner ideale, es. rimosse per contenuto minori): {saltati_no_foto_pi}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
