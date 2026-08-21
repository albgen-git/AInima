"""
simulate_matching.py
Prima simulazione della pipeline di matching (Ainima_Algoritmo_Ranking_Finale_v1.md)
su un piccolo campione di utenti dal pool di 1000 profili di test.

Cosa implementa, con i dati oggi disponibili:
  STEP 0  Filtri hard: età reciproca, distanza (haversine su coordinate_gps),
          compatibilità genere/orientamento cercato, coerenza figli,
          esclusione red_flags_rilevati.
  STEP 1  BigFive_Score — formula da §3 del documento, sulle 5 dimensioni
          globali (i facet C7-10/O8-10/E4-6 non sono nel dataset: nota
          come limitazione, non simulati separatamente).
  STEP 2  EQ/Attaccamento — formula esatta da §4 (maturità con penalità a
          soglia + valore atteso sulla matrice di compatibilità attaccamento).
  STEP 3  Coerenza Narrativa — NON disponibile (richiede i Prompt 3a/3b/4
          via LLM, non ancora generati). Placeholder neutro 0.5, come da
          regola dei documenti stessi per l'informazione mancante.
  STEP 4  Preferenze Soft — solo sulle sotto-componenti che abbiamo
          (altezza, fumo, alcol, importanza religione).
  Tie-break visivo — se il migliore e il secondo classificato hanno
          FINAL_SCORE entro system_config.soglia_tie_break_visivo, decide
          la cosine similarity tra foto profilo candidato ed embedding
          "partner ideale" del cercatore (v. decisione RF-11b in CLAUDE.md).

Uso: python simulate_matching.py [n_campioni]
"""

import math
import sys

import numpy as np
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

ATTACH_MATRIX = {
    ("sicuro", "sicuro"): 0.95, ("sicuro", "ansioso"): 0.75, ("sicuro", "evitante"): 0.70, ("sicuro", "disorganizzato"): 0.50,
    ("ansioso", "sicuro"): 0.75, ("ansioso", "ansioso"): 0.35, ("ansioso", "evitante"): 0.20, ("ansioso", "disorganizzato"): 0.35,
    ("evitante", "sicuro"): 0.70, ("evitante", "ansioso"): 0.20, ("evitante", "evitante"): 0.40, ("evitante", "disorganizzato"): 0.35,
    ("disorganizzato", "sicuro"): 0.50, ("disorganizzato", "ansioso"): 0.35, ("disorganizzato", "evitante"): 0.35, ("disorganizzato", "disorganizzato"): 0.30,
}
STILI = ["sicuro", "ansioso", "evitante", "disorganizzato"]


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bigfive_score(a, b):
    nevro_diff = 1 - abs(a["nevroticismo"] - b["nevroticismo"])
    nevro_bonus = 0.1 if (a["nevroticismo"] + b["nevroticismo"]) / 2 < 0.3 else 0.0
    nevro = min(1.0, nevro_diff + nevro_bonus)

    coscienziosita = 1 - abs(a["coscienziosita"] - b["coscienziosita"])
    apertura = 1 - abs(a["apertura"] - b["apertura"])

    # Assertività: complementarità moderata (proxy su estroversione, no facet E4-6 nel dataset)
    diff_e = abs(a["estroversione"] - b["estroversione"])
    assertivita = max(0.0, 1 - abs(diff_e - 0.3) / 0.7)

    estroversione = 1 - abs(a["estroversione"] - b["estroversione"]) * 0.5
    gradevolezza = (a["gradevolezza"] + b["gradevolezza"]) / 2

    righe = [nevro, coscienziosita, assertivita, estroversione, gradevolezza, apertura]
    return sum(righe) / len(righe)


def eq_score(a, b):
    media = (a["maturita"] + b["maturita"]) / 2
    sbil = abs(a["maturita"] - b["maturita"])
    penalita = (sbil - 0.35) * 1.5 if sbil > 0.35 else 0.0
    punteggio_maturita = min(1.0, max(0.0, media - penalita))

    attacc_score = 0.0
    for si in STILI:
        for sj in STILI:
            attacc_score += a["attaccamento"][si] * b["attaccamento"][sj] * ATTACH_MATRIX[(si, sj)]

    return punteggio_maturita * 0.6 + attacc_score * 0.4


def soft_score(a, b):
    componenti = []
    if a["pref_altezza_min"] is not None and a["pref_altezza_max"] is not None and b["altezza_cm"] is not None:
        if a["pref_altezza_min"] <= b["altezza_cm"] <= a["pref_altezza_max"]:
            componenti.append(1.0)
        else:
            fuori = min(abs(b["altezza_cm"] - a["pref_altezza_min"]), abs(b["altezza_cm"] - a["pref_altezza_max"]))
            componenti.append(max(0.0, 1 - fuori / 20))
    if a["pref_fumo"] is not None and b["fumo"] is not None:
        componenti.append(1.0 if a["pref_fumo"] == b["fumo"] else 0.3)
    if a["pref_alcol"] is not None and b["alcol"] is not None:
        componenti.append(1.0 if a["pref_alcol"] == b["alcol"] else 0.5)
    if a["pref_importanza_religione"] is not None and b["importanza_religione"] is not None:
        componenti.append(1 - abs(a["pref_importanza_religione"] - b["importanza_religione"]) / 4)
    if not componenti:
        return 0.5
    return sum(componenti) / len(componenti)


def cosine(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def hard_filters_ok(seeker, cand, dist_km):
    if cand["red_flags"]:
        return False, "red flag sul candidato"
    if not (seeker["pref_eta_min"] <= cand["eta"] <= seeker["pref_eta_max"]):
        return False, "età candidato fuori range del cercatore"
    if not (cand["pref_eta_min"] <= seeker["eta"] <= cand["pref_eta_max"]):
        return False, "età cercatore fuori range del candidato"
    if dist_km > min(seeker["pref_distanza_max_km"], cand["pref_distanza_max_km"]):
        return False, "distanza oltre il massimo reciproco"
    if seeker["pref_genere_cercato"] and cand["genere"] != seeker["pref_genere_cercato"]:
        return False, "genere candidato non richiesto dal cercatore"
    if cand["pref_genere_cercato"] and seeker["genere"] != cand["pref_genere_cercato"]:
        return False, "genere cercatore non richiesto dal candidato"
    if seeker["pref_accetta_figli"] == "No" and cand["ha_figli"]:
        return False, "cercatore non accetta figli, candidato ne ha"
    if cand["pref_accetta_figli"] == "No" and seeker["ha_figli"]:
        return False, "candidato non accetta figli, cercatore ne ha"
    return True, None


def load_pool(cur):
    cur.execute("""
        SELECT u.user_id, u.nome, u.cognome, u.genere, u.orientamento_sessuale,
               EXTRACT(YEAR FROM age(u.data_nascita))::int AS eta, u.ha_figli,
               s.coordinate_gps[0] AS lon, s.coordinate_gps[1] AS lat,
               d.pref_genere_cercato, d.pref_eta_min, d.pref_eta_max,
               d.pref_distanza_max_km, d.pref_accetta_figli,
               sc.pref_altezza_min, sc.pref_altezza_max, sc.pref_fumo, sc.pref_alcol,
               sc.pref_importanza_religione,
               p.altezza_cm, p.fumo, p.alcol,
               p.embedding_visivo_profilo, p.embedding_visivo_partner_ideale,
               so.importanza_religione,
               ps.score_big5_estroversione, ps.score_big5_gradevolezza,
               ps.score_big5_coscienziosita, ps.score_big5_nevroticismo, ps.score_big5_apertura,
               ps.score_maturita_emotiva, ps.attaccamento_probabilita, ps.red_flags_rilevati
        FROM users u
        JOIN socio_profile s ON s.user_id = u.user_id
        JOIN dealbreaker_criteria d ON d.user_id = u.user_id
        JOIN soft_criteria sc ON sc.user_id = u.user_id
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN socio_profile so ON so.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        WHERE u.stato_account = 'Attivo'
    """)
    cols = [d.name for d in cur.description]
    pool = {}
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        pool[r["user_id"]] = {
            "nome": r["nome"], "cognome": r["cognome"], "genere": r["genere"],
            "orientamento": r["orientamento_sessuale"], "eta": r["eta"], "ha_figli": r["ha_figli"],
            "lon": r["lon"], "lat": r["lat"],
            "pref_genere_cercato": r["pref_genere_cercato"],
            "pref_eta_min": r["pref_eta_min"], "pref_eta_max": r["pref_eta_max"],
            "pref_distanza_max_km": r["pref_distanza_max_km"], "pref_accetta_figli": r["pref_accetta_figli"],
            "pref_altezza_min": r["pref_altezza_min"], "pref_altezza_max": r["pref_altezza_max"],
            "pref_fumo": r["pref_fumo"], "pref_alcol": r["pref_alcol"],
            "pref_importanza_religione": r["pref_importanza_religione"],
            "altezza_cm": r["altezza_cm"], "fumo": r["fumo"], "alcol": r["alcol"],
            "emb_profilo": r["embedding_visivo_profilo"], "emb_pi": r["embedding_visivo_partner_ideale"],
            "importanza_religione": r["importanza_religione"],
            "estroversione": r["score_big5_estroversione"], "gradevolezza": r["score_big5_gradevolezza"],
            "coscienziosita": r["score_big5_coscienziosita"], "nevroticismo": r["score_big5_nevroticismo"],
            "apertura": r["score_big5_apertura"], "maturita": r["score_maturita_emotiva"],
            "attaccamento": r["attaccamento_probabilita"], "red_flags": r["red_flags_rilevati"],
        }
    return pool


def load_config(cur):
    cur.execute("SELECT chiave, valore FROM system_config")
    return {k: float(v) for k, v in cur.fetchall()}


def build_centroidi_genere(cur):
    """Centroidi M/F sugli embedding delle foto profilo reali — usati per
    verificare se la foto 'partner ideale' di un cercatore è coerente col
    genere che sta effettivamente cercando, prima di fidarsene per il
    tie-break visivo (v. caso Andrei Longo: PI photo di una donna anziana
    su un utente che cerca uomini — la foto non va usata come segnale)."""
    cur.execute("""
        SELECT u.genere, p.embedding_visivo_profilo
        FROM users u JOIN physical_profile p ON p.user_id = u.user_id
        WHERE p.embedding_visivo_profilo IS NOT NULL
    """)
    rows = cur.fetchall()
    emb_m = [e for g, e in rows if g == "Maschile"]
    emb_f = [e for g, e in rows if g == "Femminile"]
    return np.mean(np.array(emb_m), axis=0), np.mean(np.array(emb_f), axis=0)


SOGLIA_SIMILARITA_MINIMA = 0.20
# La coerenza di genere della foto 'partner ideale' (era pi_coerente_con_preferenza,
# rimossa) era un cerotto per la qualità del dato del DB Actor di test, non un
# criterio dell'algoritmo di prodotto — un utente vero non carica la foto del
# genere sbagliato rispetto a quello che cerca. Il criterio giusto è solo: la
# somiglianza vera e propria è abbastanza forte da fidarsene? (v. feedback utente
# sul caso Miguel/Francesca: un margine di genere alto non garantiva una
# somiglianza forte — 0.097, sotto qualunque soglia ragionevole).
# Soglia 0.20 provvisoria: unico caso forte validato finora è 0.54
# (Federico/Noemi); da confermare con altri campioni.


def run_for_seeker(seeker_id, pool, cfg):
    seeker = pool[seeker_id]
    print(f"\n{'=' * 70}")
    print(f"CERCATORE: {seeker['nome']} {seeker['cognome']} — {seeker['eta']} anni, "
          f"{seeker['genere']}/{seeker['orientamento']}")
    print(f"Cerca: {seeker['pref_genere_cercato']}, età {seeker['pref_eta_min']}-{seeker['pref_eta_max']}, "
          f"entro {seeker['pref_distanza_max_km']}km")

    if seeker["red_flags"]:
        print("!! Il cercatore stesso ha red flag attivi: da inviare a revisione umana, matching sospeso.")
        return

    candidati = []
    scartati = 0
    for cand_id, cand in pool.items():
        if cand_id == seeker_id:
            continue
        dist = haversine_km(seeker["lon"], seeker["lat"], cand["lon"], cand["lat"])
        ok, motivo = hard_filters_ok(seeker, cand, dist)
        if not ok:
            scartati += 1
            continue
        bf = bigfive_score(seeker, cand)
        eq = eq_score(seeker, cand)
        narr = 0.5  # N/D: richiede Prompt 3a/3b/4 via LLM
        # bidirezionale, stesso principio della coerenza narrativa nei documenti:
        # non basta che il candidato piaccia al cercatore, vale anche il contrario
        soft = (soft_score(seeker, cand) + soft_score(cand, seeker)) / 2
        final = (cfg["weight_bigfive"] * bf + cfg["weight_eq_attaccamento"] * eq +
                 cfg["weight_narrativa"] * narr + cfg["weight_preferenze_soft"] * soft)
        candidati.append({
            "id": cand_id, "cand": cand, "dist": dist,
            "bf": bf, "eq": eq, "narr": narr, "soft": soft, "final": final,
        })

    print(f"Pool totale: {len(pool) - 1} | esclusi da filtri hard: {scartati} | "
          f"sopravvissuti: {len(candidati)}")

    if not candidati:
        print("Nessun candidato sopravvive ai filtri hard. Nessuna proposta questo mese.")
        return

    candidati.sort(key=lambda c: c["final"], reverse=True)
    migliore = candidati[0]

    if migliore["final"] < cfg["soglia_minima_proposta"]:
        print(f"Miglior punteggio {migliore['final']:.3f} sotto soglia minima "
              f"{cfg['soglia_minima_proposta']:.2f} -> Slow Matching, nessuna proposta questo mese.")
        return

    # tie-break visivo tra i candidati entro soglia_tie_break_visivo dal migliore
    # BIDIREZIONALE: media tra "candidato somiglia all'ideale del cercatore" e
    # "cercatore somiglia all'ideale del candidato" — stesso principio della
    # coerenza narrativa bidirezionale già usata nei documenti (v. feedback utente
    # sul caso Vera/Luigi: un tie-break a senso unico può proporre un match che il
    # candidato stesso troverebbe poco convincente).
    soglia_tb = cfg["soglia_tie_break_visivo"]
    pari_merito = [c for c in candidati if migliore["final"] - c["final"] <= soglia_tb]
    vincitore = migliore
    tie_break_usato = False

    def media_visiva_bidirezionale(cand_entry):
        """Media delle due direzioni (candidato vs ideale del cercatore,
        cercatore vs ideale del candidato), qualunque sia il segno — un
        valore negativo in una direzione abbassa la media invece di essere
        semplicemente ignorato, così un segnale forte a senso unico (v. caso
        James/Pietro: 0.33 e -0.03) non basta più da solo a vincere."""
        cand = cand_entry["cand"]
        sims = []
        if seeker["emb_pi"] is not None and cand["emb_profilo"] is not None:
            sims.append(cosine(seeker["emb_pi"], cand["emb_profilo"]))
        if cand["emb_pi"] is not None and seeker["emb_profilo"] is not None:
            sims.append(cosine(cand["emb_pi"], seeker["emb_profilo"]))
        if not sims:
            return None
        return sum(sims) / len(sims)

    if len(pari_merito) > 1:
        medie = {id(c): media_visiva_bidirezionale(c) for c in pari_merito}
        candidati_con_media = [c for c in pari_merito if medie[id(c)] is not None]
        migliore_media = max((medie[id(c)] for c in candidati_con_media), default=None)
        if migliore_media is not None and migliore_media >= SOGLIA_SIMILARITA_MINIMA:
            pari_merito.sort(key=lambda c: medie[id(c)] if medie[id(c)] is not None else -1, reverse=True)
            vincitore = pari_merito[0]
            tie_break_usato = True
            print(f"    (tie-break visivo: media bidirezionale più alta = {migliore_media:.3f}, "
                  f"soglia {SOGLIA_SIMILARITA_MINIMA})")
        else:
            print(f"    ({len(pari_merito)} candidati pari merito, ma la media bidirezionale migliore "
                  f"({migliore_media if migliore_media is not None else 'N/D'}) non raggiunge la soglia "
                  f"{SOGLIA_SIMILARITA_MINIMA} — tie-break visivo saltato, resta il punteggio puro)")

    v = vincitore["cand"]
    print(f"\n>>> PROPOSTA: {v['nome']} {v['cognome']} — {v['eta']} anni, "
          f"{v['genere']}/{v['orientamento']}, {vincitore['dist']:.1f} km")
    print(f"    FINAL_SCORE = {vincitore['final']:.3f}  "
          f"(BigFive={vincitore['bf']:.2f}, EQ={vincitore['eq']:.2f}, "
          f"Narrativa=N/D(0.50), Soft={vincitore['soft']:.2f})")
    if tie_break_usato:
        print(f"    Tie-break visivo attivato: {len(pari_merito)} candidati entro {soglia_tb} "
              f"dal punteggio migliore, scelto per somiglianza alla foto 'partner ideale'.")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
    )
    cur = conn.cursor()
    pool = load_pool(cur)
    cfg = load_config(cur)
    print(f"Pool caricato: {len(pool)} utenti attivi. Pesi: {cfg}")

    cur.execute("""
        SELECT user_id FROM users
        WHERE stato_account='Attivo'
        ORDER BY source_actor_id LIMIT %s
    """, (n,))
    seed_ids = [r[0] for r in cur.fetchall()]

    for sid in seed_ids:
        run_for_seeker(sid, pool, cfg)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
