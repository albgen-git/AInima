"""Migrazione/seed live: fixture di account REALI da preservare sempre nel
DB (v. CLAUDE.md — richiesta esplicita dell'utente, 2026-09-03).

Perché esiste: a differenza dei 1000 profili demo (`source_actor_id IS
NOT NULL`, mirrorati da scripts/seed_render_from_local.py), un account
REALE creato passando dal wizard di onboarding vero (`source_actor_id`
NULL) non è coperto da nessuno script di seed esistente — se il DB di
collaudo su Render viene azzerato (Render lo fa automaticamente ogni
mese sul piano gratuito, v. docstring di seed_render_from_local.py),
quell'account sparisce senza che nulla lo ricrei. Scoperto dal vivo:
l'account reale dell'utente (albgen@gmail.com, "Alberto Genovese",
completato interamente via onboarding reale il 31/08, usato per gran
parte dei test di questa sessione — analisi di coppia, report
personale, il match confermato con Patrizia) esiste oggi SOLO su
Render, un unico punto di fallimento.

Questo script è DELIBERATAMENTE SEPARATO da seed_render_from_local.py
(non aggiunge questa logica lì) — quello script gestisce un pool di
1000 profili generati proceduralmente, questo gestisce un singolo
account reale con dati scritti a mano nel codice: unire le due logiche
avrebbe reso più fragile lo script già validato e verificato in questa
stessa sessione (1000/1000 conteggi coincidenti locale/Render).

I dati sotto sono stati esportati da Render il 2026-09-03 (stato
"Attivo", match con Patrizia "Confermato", contatto scambiato) — non
generati, sono gli stessi dati reali inseriti dall'utente durante il
test end-to-end. Le foto restano su R2 (object storage, non toccato da
un reset del solo Postgres) — questo script ricrea solo le righe DB che
puntano a quegli URL già esistenti, non ricarica alcun file.

Idempotente (UPSERT per user_id, sicuro da rilanciare). Rimuove anche,
se presente, uno stub di registrazione abbandonata con la stessa email
ma user_id diverso (nome/cognome mai compilati, stato 'In attesa',
trovato nel DB locale il 2026-09-03) — altrimenti il vincolo UNIQUE su
users.email farebbe fallire l'upsert.

Uso:
    python scripts/seed_real_test_fixtures.py            (DB locale)
    python scripts/seed_real_test_fixtures.py --render    (DB Render)
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

ALBERTO_UID = "cbee971b-10f1-44d3-b35b-751cb81ff906"
PATRIZIA_UID = "575b1537-adc2-4b40-a94b-3038f9054451"  # profilo demo (source_actor_id=274), già coperto da seed_render_from_local.py — qui solo per ricreare il match
MATCH_ID = "1f4486d8-384e-46cc-bf4c-a638f80f049d"

USERS = {
    "user_id": ALBERTO_UID, "nome": "Alberto", "cognome": "Genovese", "email": "albgen@gmail.com",
    "email_verificata": True, "telefono": "+393470407985", "data_nascita": "1970-04-29",
    "genere": "Maschile", "orientamento_sessuale": "Eterosessuale", "stato_civile": "Celibe/Nubile",
    "ha_figli": True, "stato_account": "Attivo", "livello_abbonamento": "Free",
    "metodo_pagamento_token": "tok_sim_", "consenso_dati_sensibili": True,
    "consenso_dati_sensibili_at": "2026-09-01 13:35:47.157470+00:00",
    "mercato": "Milano", "valuta": "EUR", "locale": "it-IT",
    "source_actor_id": None,
}

PHYSICAL_PROFILE = {
    "user_id": ALBERTO_UID, "altezza_cm": 170, "peso_kg": 75.0, "corporatura": "Media",
    "colore_capelli": "Grigio ", "colore_occhi": "Castani", "fumo": False, "alcol": True,
    "stile_vita_sport": "Palestra 2 volte la settimana ",
    "foto_profilo_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/profilo/cbee971b-10f1-44d3-b35b-751cb81ff906.jpg",
    "foto_partner_ideale_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/partner_ideale/cbee971b-10f1-44d3-b35b-751cb81ff906.jpg",
}

SOCIO_PROFILE = {
    "user_id": ALBERTO_UID, "comune_residenza": "Cologno Monzese ", "lon": 9.2803, "lat": 45.5422,
    "titolo_studio": "Laurea triennale", "settore_occupazionale": "Informatica ",
    "fascia_reddito": "45.000€ - 70.000€", "fede_religiosa": "Ateo", "importanza_religione": 1,
    "importanza_vicinanza_geografica": 0.5, "lingue_parlate": ["Italiano"],
}

DEALBREAKER = {
    "user_id": ALBERTO_UID, "pref_genere_cercato": "Femminile", "pref_orientamento_compatibile": None,
    "pref_eta_min": 35, "pref_eta_max": 45, "pref_accetta_figli": "Si", "pref_desidera_figli_futuri": "No",
}

SOFT_CRITERIA = {
    "user_id": ALBERTO_UID, "pref_altezza_min": 155, "pref_altezza_max": 175,
    "pref_stato_civile_accettato": "Nubile", "pref_titolo_studio": "Laurea", "pref_corporatura": "Media",
    "pref_fumo": False, "pref_alcol": None,
    # pref_fede_religiosa/pref_importanza_religione: mancanti nell'export
    # iniziale (v. CLAUDE.md), ridomandate all'utente e risposte il
    # 2026-09-04 — pref_alcol resta None, "nessuna preferenza" è la
    # risposta data, non un campo ancora da colmare.
    "pref_fede_religiosa": "Nessuna preferenza", "pref_importanza_religione": 2,
}

PSYCHOMETRIC = {
    "user_id": ALBERTO_UID,
    "score_big5_estroversione": 0.25, "score_big5_gradevolezza": 0.8125, "score_big5_coscienziosita": 0.875,
    "score_big5_nevroticismo": 0.46875, "score_big5_apertura": 0.875,
    "confidenza_big5_estroversione": 1.0, "confidenza_big5_gradevolezza": 1.0,
    "confidenza_big5_coscienziosita": 1.0, "confidenza_big5_nevroticismo": 1.0, "confidenza_big5_apertura": 1.0,
    "ansia_score": 0.19444445, "evitamento_score": 0.5555556, "stile_attaccamento": "Evitante",
    "confidenza_attaccamento_ansia": 1.0, "confidenza_attaccamento_evitamento": 0.6,
    "eq_pilastro_autoconsapevolezza": 0.5416667, "eq_pilastro_autoregolazione": 0.9166667,
    "eq_pilastro_empatia": 0.625, "eq_pilastro_responsabilita": 0.7916667, "score_maturita_emotiva": 0.71875,
    "confidenza_eq_autoconsapevolezza": 1.0, "confidenza_eq_autoregolazione": 1.0,
    "confidenza_eq_empatia": 1.0, "confidenza_eq_responsabilita": 1.0,
    "confidenza_eq_autoregolazione_interna": 1.0, "confidenza_eq_empatia_interna": 1.0,
    "flag_profilo_per_revisione_dati": False, "flag_trappola_fallita": 0,
    "profilo_valori_self": {"bisogno_stabilita": 0.75, "crescita_personale": 0.5, "centralita_famiglia": 1.0, "orientamento_carriera": 0.5},
    "profilo_valori_partner_ideale": {"bisogno_stabilita": 0.5, "crescita_personale": 0.75, "centralita_famiglia": 1.0, "orientamento_carriera": 0.75},
    "profilo_stile_vita_self": {"socialita": 0.25, "ritmo_vita": 0.25, "organizzazione": 1.0},
    "profilo_stile_vita_partner_ideale": {"socialita": 0.5, "ritmo_vita": 0.25, "organizzazione": 1.0},
    "profilo_dinamica_relazionale_self": {"autonomia_fusione": 0.75, "condivisione_ruoli": 0.75, "espressivita_emotiva": 0.25},
    "profilo_dinamica_relazionale_partner_ideale": {"autonomia_fusione": 1.0, "condivisione_ruoli": 1.0, "espressivita_emotiva": 1.0},
    "profilo_aspirazioni_self": {"mobilita_geografica": 0.75, "impegno_lungo_termine": 1.0, "orizzonte_progettuale": 0.75},
    "profilo_aspirazioni_partner_ideale": {"mobilita_geografica": 0.75, "impegno_lungo_termine": 1.0, "orizzonte_progettuale": 0.75},
}

INTEREST_TAGS = {
    "user_id": ALBERTO_UID,
    "mi_piace": "Cinema, cucinare, sport, viaggi", "non_sopporto": "Animali, fumo",
    "partner_vorrei": "Socievole, allegra, positiva ", "partner_non_vorrei": "Egocentrismo, invidia, pregiudizio",
    "mi_piace_tags": ["cinema", "cucinare", "sport", "viaggi"],
    "non_sopporto_tags": ["animali", "fumo"],
    "partner_vorrei_tags": ["socievole", "allegra", "positiva"],
    "partner_non_vorrei_tags": ["egocentrismo", "invidia", "pregiudizio"],
}

PROFILE_NARRATIVE = {
    "user_id": ALBERTO_UID,
    "descrizione_di_se": "Sono una persona seria, razionale. Mi piace stare con gli amici e con la mia famiglia. Mi piace viaggiare, il cinema, la televisione e i giochi. Faccio sport ma non sono in fissato. ",
    "descrizione_partner_ideale": "Cerco una donna seria, intelligente, spiritosa, allegra. Che condivida le mie  passioni. Capace di ascoltare e di sostenermi. ",
}

# uuid[] — cast esplicito richiesto (v. CLAUDE.md: psycopg2 adatta di
# default una lista Python di stringhe a text[], non uuid[]).
SHORTLIST_CANDIDATI = [PATRIZIA_UID, "59730b3d-57c0-4bb8-ae87-867bbc6a98c1"]

MATCH = {
    "match_id": MATCH_ID, "user_a_id": ALBERTO_UID, "user_b_id": PATRIZIA_UID, "stato": "Confermato",
    "final_score": 0.6228116, "pagamento_a_stato": "Pagato", "pagamento_b_stato": "Pagato",
    "contatto_scambiato": True, "selezionato_per_somiglianza_visiva": False,
    "flag_rifiuto_esplicito": False, "flag_asimmetria_narrativa": False, "algoritmo_versione": "stable_v8",
    # snapshot COMPLETO di system_config al momento del match reale (v.
    # matches.algoritmo_parametri, schema.sql) — tutti i valori, non un
    # sottoinsieme scelto a mano, altrimenti la fixture non è più una
    # riproduzione esatta del dato reale originale.
    "algoritmo_parametri": {
        "weight_bigfive": 0.3, "weight_narrativa": 0.2, "weight_eq_empatia": 0.25,
        "jwt_scadenza_giorni": 30.0, "otp_scadenza_minuti": 10.0, "otp_tentativi_massimi": 5.0,
        "report_top_candidates": 10.0, "soglia_area_urbana_km": 50.0,
        "soglia_minima_proposta": 0.55, "weight_eq_attaccamento": 0.35, "weight_preferenze_soft": 0.15,
        "mesi_esclusione_rimatch": 6.0, "fee_match_confermato_eur": 15.0, "weight_eq_responsabilita": 0.25,
        "otp_rate_limit_ip_per_ora": 10.0, "weight_eq_autoregolazione": 0.25,
        "recupero_accesso_grazia_ore": 48.0, "weight_eq_autoconsapevolezza": 0.25,
        "finestra_risposta_match_giorni": 7.0, "otp_richiesta_cooldown_secondi": 60.0,
        "cadenza_email_engagement_giorni": 7.0, "giorno_esecuzione_ciclo_mensile": 1.0,
        "soglia_similarita_visiva_minima": 0.2, "dimensione_shortlist_analisi_visiva": 5.0,
        "soglia_percentile_similarita_visiva": 0.9, "soglia_importanza_vicinanza_esclusione": 0.6,
    },
    "analisi_caratteriale_coppia": (
        "Il vostro abbinamento nasce da alcune affinità concrete, insieme a un'area su cui vale "
        "la pena costruire dialogo fin da subito.\n\nCosa vi avvicina:\n"
        "• Apertura mentale — Condividete una spiccata curiosità intellettuale e culturale verso il "
        "mondo, che rende naturale stimolarsi a vicenda con nuove idee e prospettive.\n"
        "• Gradevolezza — La relazione poggia su una base di gentilezza e attenzione reciproca che "
        "facilita l'ascolto e la cura del legame nel quotidiano.\n\n"
        "Su cosa vale la pena dialogare:\n"
        "• Dinamica relazionale — La gestione dei momenti di intimità e vicinanza potrebbe risentire "
        "di bisogni differenti da sincronizzare, rendendo prezioso il dialogo aperto sui propri "
        "confini personali."
    ),
}


def _upsert(cur, tabella, dati, pk="user_id"):
    colonne = list(dati.keys())
    valori = []
    for c in colonne:
        v = dati[c]
        valori.append(json.dumps(v) if isinstance(v, dict) else v)
    placeholders = []
    for c in colonne:
        if isinstance(dati[c], dict):
            placeholders.append("%s::jsonb")
        else:
            placeholders.append("%s")
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in colonne if c != pk)
    sql = (
        f"INSERT INTO {tabella} ({', '.join(colonne)}) VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT ({pk}) DO UPDATE SET {set_clause}"
    )
    cur.execute(sql, valori)


def main():
    if "--render" in sys.argv:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        from db import get_conn  # noqa: E402

        conn = get_conn()

    cur = conn.cursor()

    # Stub di registrazione abbandonata con la stessa email, user_id diverso
    # (nome/cognome mai compilati) — rimosso prima, altrimenti il vincolo
    # UNIQUE su users.email fa fallire l'upsert sotto.
    cur.execute(
        "DELETE FROM users WHERE email = %s AND user_id != %s AND nome IS NULL",
        (USERS["email"], ALBERTO_UID),
    )
    if cur.rowcount:
        print(f"Rimosso {cur.rowcount} stub di registrazione abbandonata con la stessa email.")

    # users e physical_profile PRIMA di tutto il resto — ogni altra tabella
    # satellite ha una FK su user_id, l'ordine qui non è arbitrario (trovato
    # dal vivo: un primo tentativo con socio_profile prima ha violato la FK).
    _upsert(cur, "users", USERS)
    _upsert(cur, "physical_profile", PHYSICAL_PROFILE)

    # socio_profile.coordinate_gps è un tipo point, non esprimibile con
    # l'helper generico _upsert() sopra (richiede point(%s, %s), non un
    # singolo placeholder) — gestito qui a parte, stesso pattern già usato
    # in routers/profile.py per lo stesso campo.
    socio = dict(SOCIO_PROFILE)
    lon, lat = socio.pop("lon"), socio.pop("lat")
    colonne_socio = list(socio.keys())
    set_clause_socio = ", ".join(f"{c} = EXCLUDED.{c}" for c in colonne_socio if c != "user_id")
    cur.execute(
        f"""
        INSERT INTO socio_profile ({', '.join(colonne_socio)}, coordinate_gps)
        VALUES ({', '.join(['%s'] * len(colonne_socio))}, point(%s, %s))
        ON CONFLICT (user_id) DO UPDATE SET {set_clause_socio}, coordinate_gps = point(%s, %s)
        """,
        [socio[c] for c in colonne_socio] + [lon, lat, lon, lat],
    )

    _upsert(cur, "dealbreaker_criteria", DEALBREAKER)
    _upsert(cur, "soft_criteria", SOFT_CRITERIA)
    _upsert(cur, "psychometric_scores", PSYCHOMETRIC)
    _upsert(cur, "interest_tags", INTEREST_TAGS)
    _upsert(cur, "profile_narrative", PROFILE_NARRATIVE)

    # Il match dipende da Patrizia (profilo demo, source_actor_id=274) —
    # già garantita dal seed del pool demo con lo stesso user_id, quindi la
    # FK qui sotto è sicura anche su un DB appena riseedato in quest'ordine
    # (demo pool prima, poi questo script).
    _upsert(cur, "matches", MATCH, pk="match_id")
    # shortlist_candidati (uuid[]) a parte, stesso motivo di coordinate_gps
    # sopra — non esprimibile con l'helper generico _upsert().
    cur.execute(
        "UPDATE matches SET shortlist_candidati = %s::uuid[] WHERE match_id = %s",
        (SHORTLIST_CANDIDATI, MATCH_ID),
    )

    conn.commit()
    print("Fixture 'Alberto Genovese' (albgen@gmail.com) + match confermato con Patrizia: inseriti/aggiornati.")
    conn.close()


if __name__ == "__main__":
    main()
