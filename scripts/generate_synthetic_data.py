"""
generate_synthetic_data.py
Completa i 1000 profili importati dal DB Actor con i dati che quel
dataset non conteneva: contatti/account, geolocalizzazione Milano,
criteri di ricerca (dealbreaker/soft) e punteggi psicometrici/EQ.

Tutto generato con RNG seedato sul source_actor_id (riproducibile).

NON generato in questo script (richiede chiamate LLM reali, v. i
prompt in docs/): self_profile_canonico, ideal_partner_profile_canonico,
self_embedding_vector, ideal_embedding_vector, report_prontezza_relazionale.
Questi campi restano NULL — passo successivo separato.

Uso: python generate_synthetic_data.py
"""

import datetime
import os
import random

import numpy as np
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# ── Comuni Milano + hinterland, con coordinate reali (lat, lon) ───────────────
# Peso più alto su Milano città, coda lunga verso Lodi/Pavia per dare varietà
# di distanza utile a testare pref_distanza_max_km.
COMUNI = [
    ("Milano", 45.4642, 9.1900, 40),
    ("Sesto San Giovanni", 45.5344, 9.2361, 6),
    ("Cinisello Balsamo", 45.5548, 9.2166, 5),
    ("Monza", 45.5845, 9.2744, 6),
    ("Rho", 45.5311, 9.0388, 4),
    ("Legnano", 45.5960, 8.9160, 3),
    ("Cologno Monzese", 45.5306, 9.2775, 4),
    ("San Donato Milanese", 45.4064, 9.2716, 4),
    ("Corsico", 45.4394, 9.1000, 3),
    ("Rozzano", 45.3833, 9.1333, 3),
    ("Cernusco sul Naviglio", 45.5175, 9.3313, 3),
    ("Segrate", 45.4919, 9.3122, 3),
    ("Bresso", 45.5450, 9.1875, 3),
    ("Paderno Dugnano", 45.5713, 9.1596, 3),
    ("Vimercate", 45.6167, 9.3667, 3),
    ("Lodi", 45.3142, 9.5034, 4),
    ("Pavia", 45.1847, 9.1582, 3),
]
COMUNE_WEIGHTS = [c[3] for c in COMUNI]

STATO_CIVILE = ["Celibe/Nubile", "Divorziato/a", "Vedovo/a", "Separato/a"]
STATO_CIVILE_WEIGHTS = [70, 20, 5, 5]

FIGLI_OPZIONI_ACCETTA = ["Si", "No", "Indifferente"]
FIGLI_OPZIONI_DESIDERA = ["Si", "No", "Da valutare"]


def opposite_or_same_genere(genere: str, orientamento: str, rng: random.Random) -> str:
    """Deriva un genere cercato plausibile in base a genere/orientamento
    dell'utente stesso — stessa logica di massima usata in generate_pi.py
    del DB Actor per coerenza col dataset di origine."""
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
    # Bisessuale / Pansessuale / Asessuale / Altro: nessun genere escludente
    return rng.choice(["Maschile", "Femminile", "Non binario", "Altro"])


def main():
    conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, source_actor_id, nome, cognome, genere,
               orientamento_sessuale, data_nascita
        FROM users WHERE source_actor_id IS NOT NULL ORDER BY source_actor_id
    """)
    rows = cur.fetchall()
    print(f"Utenti da completare: {len(rows)}")

    oggi = datetime.date.today()
    n_revisione_umana = 0

    for user_id, actor_id, nome, cognome, genere, orientamento, data_nascita in rows:
        seed = actor_id * 7919
        rng = random.Random(seed)
        np_rng = np.random.default_rng(seed)

        eta = (oggi - data_nascita).days // 365

        # ── users: contatti + stato civile + consenso (dati di test) ──────
        email = f"{nome.lower()}.{cognome.lower()}.{actor_id}@test.ainima.local".replace(" ", "")
        telefono = f"+393{rng.randint(0, 9)}{rng.randint(1000000, 9999999)}"
        stato_civile = rng.choices(STATO_CIVILE, weights=STATO_CIVILE_WEIGHTS, k=1)[0]
        ha_figli = rng.random() < (0.55 if eta > 40 else 0.15)

        cur.execute(
            """
            UPDATE users SET
                email = %s, telefono = %s,
                stato_civile = %s, ha_figli = %s,
                consenso_dati_sensibili = TRUE, consenso_dati_sensibili_at = now()
            WHERE user_id = %s
            """,
            (email, telefono, stato_civile, ha_figli, str(user_id)),
        )

        # ── socio_profile: geolocalizzazione Milano/hinterland ─────────────
        comune, lat, lon, _ = rng.choices(COMUNI, weights=COMUNE_WEIGHTS, k=1)[0]
        # piccolo jitter per non impilare tutti sullo stesso punto del comune
        lat_j = lat + rng.uniform(-0.01, 0.01)
        lon_j = lon + rng.uniform(-0.01, 0.01)
        cur.execute(
            """
            UPDATE socio_profile SET comune_residenza = %s,
                coordinate_gps = point(%s, %s)
            WHERE user_id = %s
            """,
            (comune, lon_j, lat_j, str(user_id)),
        )

        # ── dealbreaker_criteria ────────────────────────────────────────
        pref_genere = opposite_or_same_genere(genere, orientamento, rng)
        eta_spread = rng.randint(5, 12)
        pref_eta_min = max(18, eta - eta_spread)
        pref_eta_max = min(99, eta + eta_spread)
        # pref_distanza_max_km RIMOSSO (SUPERATO) — v. Ainima_Algoritmo_Ranking_Finale_v1.md
        # §3bis, sostituito da socio_profile.importanza_vicinanza_geografica/lingue_parlate
        cur.execute(
            """
            INSERT INTO dealbreaker_criteria (
                user_id, pref_genere_cercato, pref_eta_min, pref_eta_max,
                pref_accetta_figli, pref_desidera_figli_futuri
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                str(user_id), pref_genere, pref_eta_min, pref_eta_max,
                rng.choice(FIGLI_OPZIONI_ACCETTA), rng.choice(FIGLI_OPZIONI_DESIDERA),
            ),
        )

        # ── soft_criteria ────────────────────────────────────────────────
        alt_min = rng.randint(150, 175)
        alt_max = alt_min + rng.randint(10, 30)
        cur.execute(
            """
            INSERT INTO soft_criteria (
                user_id, pref_altezza_min, pref_altezza_max,
                pref_fumo, pref_alcol, pref_importanza_religione
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                str(user_id), alt_min, alt_max,
                rng.choice([True, False, None]), rng.choice([True, False, None]),
                rng.choice([1, 2, 3, 4, 5, None]),
            ),
        )

        # ── psychometric_scores: Big Five + EQ + attaccamento ──────────────
        # Aggiornato 2026-08-19 (v. CLAUDE.md): niente più chat simulata —
        # attaccamento è ora ansia_score/evitamento_score continui
        # (Ainima_Test_Attaccamento_v1.md) invece della distribuzione
        # Dirichlet a 4 stili, ed EQ/flag di revisione derivano dagli stessi
        # test scritti deterministici usati a runtime (v.
        # routers/psychometric.py._ricalcola_flag_revisione_dati, duplicata
        # qui identica per coerenza col comportamento reale del sistema).
        #
        # Tentativo 1 (Big Five spostato correlato) e tentativo 2 (solo EQ/
        # attaccamento) erano falliti per lo stesso motivo del mondo
        # pre-2026-08-19 (v. CLAUDE.md) — il tentativo 3 che segue peggiora
        # più dimensioni insieme, scegliendo quelle immuni al clustering
        # (gradevolezza è una MEDIA come la maturità, non una differenza;
        # coscienziosità/apertura/nevroticismo spostati su valori estremi
        # pesano contro l'85% del pool "normale" anche se non tra due atipici).
        atipico = rng.random() < 0.15
        if atipico:
            big5 = {
                "estroversione": float(np.clip(np_rng.normal(0.30, 0.12), 0.0, 1.0)),
                "gradevolezza": float(np.clip(np_rng.normal(0.12, 0.08), 0.0, 1.0)),  # media, non differenza
                "coscienziosita": float(np.clip(np_rng.normal(0.20, 0.10), 0.0, 1.0)),
                "nevroticismo": float(np.clip(np_rng.normal(0.82, 0.10), 0.0, 1.0)),  # niente bonus "media bassa"
                "apertura": float(np.clip(np_rng.normal(0.20, 0.10), 0.0, 1.0)),
            }
            eq_pilastri = [float(np.clip(np_rng.normal(0.15, 0.10), 0.0, 1.0)) for _ in range(4)]
            ansia_score = float(np.clip(np_rng.normal(0.75, 0.15), 0.0, 1.0))
            evitamento_score = float(np.clip(np_rng.normal(0.70, 0.15), 0.0, 1.0))
        else:
            big5 = {
                trait: float(np.clip(np_rng.normal(0.5, 0.18), 0.0, 1.0))
                for trait in ["estroversione", "gradevolezza", "coscienziosita", "nevroticismo", "apertura"]
            }
            eq_pilastri = [float(np.clip(np_rng.normal(0.55, 0.20), 0.0, 1.0)) for _ in range(4)]
            ansia_score = float(np.clip(np_rng.normal(0.35, 0.18), 0.0, 1.0))
            evitamento_score = float(np.clip(np_rng.normal(0.35, 0.18), 0.0, 1.0))
        score_maturita = sum(eq_pilastri) / 4
        eq_autoconsapevolezza, eq_autoregolazione, eq_empatia, eq_responsabilita = eq_pilastri

        if ansia_score < 0.5 and evitamento_score < 0.5:
            stile_attaccamento = "Sicuro"
        elif ansia_score >= 0.5 and evitamento_score < 0.5:
            stile_attaccamento = "Ansioso"
        elif ansia_score < 0.5 and evitamento_score >= 0.5:
            stile_attaccamento = "Evitante"
        else:
            stile_attaccamento = "Timoroso/Disorganizzato"

        # Stessa formula di routers/psychometric.py._ricalcola_flag_revisione_dati
        # (Ainima_Test_EQScore_v1.md §4 + Ainima_Algoritmo_Ranking_Finale_v1.md §10)
        n_incoerenze = 0
        if abs(big5["nevroticismo"] - (1 - eq_autoregolazione)) > 0.5:
            n_incoerenze += 1
        if abs(big5["coscienziosita"] - eq_autoregolazione) > 0.5:
            n_incoerenze += 1
        if abs((1 - big5["gradevolezza"]) - (1 - eq_empatia)) > 0.5:
            n_incoerenze += 1
        quadrante_timoroso = ansia_score > 0.7 and evitamento_score > 0.7
        flag_revisione_dati = n_incoerenze >= 2 or quadrante_timoroso
        if flag_revisione_dati:
            n_revisione_umana += 1

        cur.execute(
            """
            INSERT INTO psychometric_scores (
                user_id, score_big5_estroversione, score_big5_gradevolezza,
                score_big5_coscienziosita, score_big5_nevroticismo, score_big5_apertura,
                score_maturita_emotiva,
                eq_pilastro_autoconsapevolezza, eq_pilastro_autoregolazione,
                eq_pilastro_empatia, eq_pilastro_responsabilita,
                ansia_score, evitamento_score, stile_attaccamento,
                flag_profilo_per_revisione_dati
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                score_big5_estroversione = EXCLUDED.score_big5_estroversione,
                score_big5_gradevolezza = EXCLUDED.score_big5_gradevolezza,
                score_big5_coscienziosita = EXCLUDED.score_big5_coscienziosita,
                score_big5_nevroticismo = EXCLUDED.score_big5_nevroticismo,
                score_big5_apertura = EXCLUDED.score_big5_apertura,
                score_maturita_emotiva = EXCLUDED.score_maturita_emotiva,
                eq_pilastro_autoconsapevolezza = EXCLUDED.eq_pilastro_autoconsapevolezza,
                eq_pilastro_autoregolazione = EXCLUDED.eq_pilastro_autoregolazione,
                eq_pilastro_empatia = EXCLUDED.eq_pilastro_empatia,
                eq_pilastro_responsabilita = EXCLUDED.eq_pilastro_responsabilita,
                ansia_score = EXCLUDED.ansia_score,
                evitamento_score = EXCLUDED.evitamento_score,
                stile_attaccamento = EXCLUDED.stile_attaccamento,
                flag_profilo_per_revisione_dati = EXCLUDED.flag_profilo_per_revisione_dati
            """,
            (
                str(user_id), big5["estroversione"], big5["gradevolezza"],
                big5["coscienziosita"], big5["nevroticismo"], big5["apertura"],
                score_maturita, eq_autoconsapevolezza, eq_autoregolazione, eq_empatia, eq_responsabilita,
                ansia_score, evitamento_score, stile_attaccamento, flag_revisione_dati,
            ),
        )

    conn.commit()
    print("Completato.")
    print(f"  Profili con flag_profilo_per_revisione_dati (incoerenza statistica o quadrante Timoroso/Disorganizzato): {n_revisione_umana}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
