"""Migrazione/seed live: fixture di account REALI da preservare sempre nel
DB (v. CLAUDE.md — richiesta esplicita dell'utente, 2026-09-03; esteso a
Danae Almeida il 2026-09-05, stessa richiesta/motivazione).

Perché esiste: a differenza dei 1000 profili demo (`source_actor_id IS
NOT NULL`, mirrorati da scripts/seed_render_from_local.py), un account
REALE creato passando dal wizard di onboarding vero (`source_actor_id`
NULL) non è coperto da nessuno script di seed esistente — se il DB di
collaudo su Render viene azzerato (Render lo fa automaticamente ogni
mese sul piano gratuito, v. docstring di seed_render_from_local.py),
quell'account sparisce senza che nulla lo ricrei. Scoperto dal vivo per
Alberto Genovese (albgen@gmail.com) il 2026-09-03; esteso a Danae Almeida
(danaestefania.al@gmail.com) dopo che l'utente ha chiesto esplicitamente
di non ripetere lo stesso rischio ora che anche lei ha dati reali degni
di nota (il match con Sebastian Rizzo creato il 2026-09-05 per risolvere
il gap lingue_parlate sul pool demo, v. CLAUDE.md).

Questo script è DELIBERATAMENTE SEPARATO da seed_render_from_local.py
(non aggiunge questa logica lì) — quello script gestisce un pool di
1000 profili generati proceduralmente, questo gestisce account reali con
dati scritti a mano nel codice: unire le due logiche avrebbe reso più
fragile lo script già validato e verificato in questa stessa sessione
(1000/1000 conteggi coincidenti locale/Render).

I dati sotto sono ESPORTATI da Render (Alberto il 2026-09-03, Danae il
2026-09-05) — non generati, sono gli stessi dati reali inseriti dagli
utenti durante i rispettivi test end-to-end, riprodotti fedelmente
INCLUSI i valori chiaramente segnaposto/di prova (es. i criteri soft e
le liste piace/detesta di Danae: "pref_altezza_max": 2001,
"pref_stato_civile_accettato": 'Single???!', tag come 'Xvg'/'Hj'/'Zdf')
— questo script ricostruisce lo stato reale del DB, non lo corregge; una
pulizia dei dati di Danae è una scelta separata, da fare (se voluta) con
lei, non silenziosamente qui. Le foto restano su R2 (object storage, non
toccato da un reset del solo Postgres) — questo script ricrea solo le
righe DB che puntano a quegli URL già esistenti, non ricarica alcun file.

Idempotente (UPSERT per user_id/match_id, sicuro da rilanciare). Rimuove
anche, per ciascuna persona, eventuali stub di registrazione abbandonata
con la stessa email ma user_id diverso — altrimenti il vincolo UNIQUE su
users.email farebbe fallire l'upsert (già capitato per Alberto).

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
ALBERTO_MATCH_ID = "1f4486d8-384e-46cc-bf4c-a638f80f049d"

DANAE_UID = "43ac592d-4179-4671-a967-eba1802acbc7"
SEBASTIAN_UID = "c75d2555-ec3b-4811-8903-d8a70a44eb9d"  # profilo demo (Monza), abbinato a Danae il 2026-09-05
DANAE_MATCH_ID = "68f129e4-6228-43a9-a11c-3d6c180a05ee"

# ─────────────────────────────────────────────────────────────────────
# Ogni persona: un dict con una chiave per tabella satellite (tutte
# indicizzate su user_id, gestite dallo stesso ciclo in main()).
# ─────────────────────────────────────────────────────────────────────
PERSONE = [
    {
        "users": {
            "user_id": ALBERTO_UID, "nome": "Alberto", "cognome": "Genovese", "email": "albgen@gmail.com",
            "email_verificata": True, "telefono": "+393470407985", "data_nascita": "1970-04-29",
            "genere": "Maschile", "orientamento_sessuale": "Eterosessuale", "stato_civile": "Celibe/Nubile",
            "ha_figli": True, "stato_account": "Attivo", "livello_abbonamento": "Free",
            "metodo_pagamento_token": "tok_sim_", "consenso_dati_sensibili": True,
            "consenso_dati_sensibili_at": "2026-09-01 13:35:47.157470+00:00",
            "mercato": "Milano", "valuta": "EUR", "locale": "it-IT",
            "source_actor_id": None, "is_demo": False,
        },
        "physical_profile": {
            "user_id": ALBERTO_UID, "altezza_cm": 170, "peso_kg": 75.0, "corporatura": "Media",
            "colore_capelli": "Grigio ", "colore_occhi": "Castani", "fumo": False, "alcol": True,
            "stile_vita_sport": "Palestra 2 volte la settimana ",
            "foto_profilo_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/profilo/cbee971b-10f1-44d3-b35b-751cb81ff906.jpg",
            "foto_partner_ideale_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/partner_ideale/cbee971b-10f1-44d3-b35b-751cb81ff906.jpg",
        },
        "socio_profile": {
            "user_id": ALBERTO_UID, "comune_residenza": "Cologno Monzese ", "lon": 9.2803, "lat": 45.5422,
            "titolo_studio": "Laurea triennale", "settore_occupazionale": "Informatica ",
            "fascia_reddito": "45.000€ - 70.000€", "fede_religiosa": "Ateo", "importanza_religione": 1,
            "importanza_vicinanza_geografica": 0.5, "lingue_parlate": ["Italiano"],
        },
        "dealbreaker_criteria": {
            "user_id": ALBERTO_UID, "pref_genere_cercato": "Femminile", "pref_orientamento_compatibile": None,
            "pref_eta_min": 35, "pref_eta_max": 45, "pref_accetta_figli": "Si", "pref_desidera_figli_futuri": "No",
        },
        "soft_criteria": {
            "user_id": ALBERTO_UID, "pref_altezza_min": 155, "pref_altezza_max": 175,
            # Array a 1 elemento — pref_stato_civile_accettato è diventato
            # TEXT[] il 2026-09-05 (multi-selezione); il valore stesso
            # ("Nubile", non canonico) resta quello originale esportato da
            # Render, non corretto (v. nota in cima al file).
            "pref_stato_civile_accettato": ["Nubile"], "pref_titolo_studio": "Laurea", "pref_corporatura": "Media",
            "pref_fumo": False, "pref_alcol": None,
            # pref_fede_religiosa/pref_importanza_religione: mancanti nell'export
            # iniziale (v. CLAUDE.md), ridomandate all'utente e risposte il
            # 2026-09-04 — pref_alcol resta None, "nessuna preferenza" è la
            # risposta data, non un campo ancora da colmare.
            "pref_fede_religiosa": "Nessuna preferenza", "pref_importanza_religione": 2,
        },
        "psychometric_scores": {
            "user_id": ALBERTO_UID,
            "score_big5_estroversione": 0.25, "score_big5_gradevolezza": 0.8125, "score_big5_coscienziosita": 0.875,
            "score_big5_nevroticismo": 0.46875, "score_big5_apertura": 0.875,
            "confidenza_big5_estroversione": 1.0, "confidenza_big5_gradevolezza": 1.0,
            "confidenza_big5_coscienziosita": 1.0, "confidenza_big5_nevroticismo": 1.0, "confidenza_big5_apertura": 1.0,
            # stile_attaccamento RIMOSSO (v. CLAUDE.md 2026-09-06) — colonna
            # non più persistita, i due punteggi sotto bastano.
            "ansia_score": 0.19444445, "evitamento_score": 0.5555556,
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
        },
        "interest_tags": {
            "user_id": ALBERTO_UID,
            "mi_piace": "Cinema, cucinare, sport, viaggi", "non_sopporto": "Animali, fumo",
            "partner_vorrei": "Socievole, allegra, positiva ", "partner_non_vorrei": "Egocentrismo, invidia, pregiudizio",
            "mi_piace_tags": ["cinema", "cucinare", "sport", "viaggi"],
            "non_sopporto_tags": ["animali", "fumo"],
            "partner_vorrei_tags": ["socievole", "allegra", "positiva"],
            "partner_non_vorrei_tags": ["egocentrismo", "invidia", "pregiudizio"],
        },
        "profile_narrative": {
            "user_id": ALBERTO_UID,
            "descrizione_di_se": "Sono una persona seria, razionale. Mi piace stare con gli amici e con la mia famiglia. Mi piace viaggiare, il cinema, la televisione e i giochi. Faccio sport ma non sono in fissato. ",
            "descrizione_partner_ideale": "Cerco una donna seria, intelligente, spiritosa, allegra. Che condivida le mie  passioni. Capace di ascoltare e di sostenermi. ",
        },
    },
    {
        "users": {
            "user_id": DANAE_UID, "nome": "Danae", "cognome": "Almeida", "email": "danaestefania.al@gmail.com",
            "email_verificata": True, "telefono": "+971544854682", "data_nascita": "1999-10-14",
            "genere": "Femminile", "orientamento_sessuale": "Eterosessuale", "stato_civile": "Celibe/Nubile",
            "ha_figli": False, "stato_account": "Attivo", "livello_abbonamento": "Free",
            "metodo_pagamento_token": "tok_sim_8943", "consenso_dati_sensibili": True,
            "consenso_dati_sensibili_at": "2026-09-03 21:19:21.410226+00:00",
            # mercato/valuta: rimasti 'Milano'/'EUR' anche su Render (mai chiesti
            # in onboarding a un utente reale, campo puramente informativo per
            # ora, v. CLAUDE.md decisione Dubai 12/08) — riprodotti fedelmente
            # com'erano, non "corretti" a Dubai/AED qui.
            "mercato": "Milano", "valuta": "EUR", "locale": "it-IT",
            "source_actor_id": None, "is_demo": False,
        },
        "physical_profile": {
            "user_id": DANAE_UID, "altezza_cm": 157, "peso_kg": 52.0, "corporatura": "Atletica",
            "colore_capelli": "Castani", "colore_occhi": "Marroni", "fumo": False, "alcol": True,
            "stile_vita_sport": "Palestra",
            "foto_profilo_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/profilo/43ac592d-4179-4671-a967-eba1802acbc7.jpeg",
            "foto_partner_ideale_url": "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev/partner_ideale/43ac592d-4179-4671-a967-eba1802acbc7.jpeg",
        },
        "socio_profile": {
            # comune_residenza/coordinate aggiornati al 2026-09-05 (v. CLAUDE.md,
            # fix lingue_parlate/redistribuzione geografica pool demo — Danae
            # stessa era già a Dubai da prima, invariata da quel fix).
            "user_id": DANAE_UID, "comune_residenza": "Dubai", "lon": 55.2708, "lat": 25.2048,
            "titolo_studio": "Laurea triennale", "settore_occupazionale": "Design ",
            "fascia_reddito": "25.000€ - 45.000€", "fede_religiosa": "Agnostica", "importanza_religione": 1,
            "importanza_vicinanza_geografica": 0.25, "lingue_parlate": ["Italiano"],
        },
        "dealbreaker_criteria": {
            "user_id": DANAE_UID, "pref_genere_cercato": "Maschile", "pref_orientamento_compatibile": None,
            "pref_eta_min": 26, "pref_eta_max": 30, "pref_accetta_figli": "Indifferente",
            "pref_desidera_figli_futuri": "Da valutare",
        },
        "soft_criteria": {
            # Valori di prova evidenti (altezza 2000-2001cm, "Single???!",
            # "A") — riprodotti fedelmente com'erano su Render, non ripuliti
            # qui (v. nota in cima al file).
            "user_id": DANAE_UID, "pref_altezza_min": 2000, "pref_altezza_max": 2001,
            "pref_stato_civile_accettato": ["Single???!"], "pref_titolo_studio": "Università ",
            "pref_corporatura": "Atletica", "pref_fumo": False, "pref_alcol": None,
            "pref_fede_religiosa": "A", "pref_importanza_religione": 1,
        },
        "psychometric_scores": {
            "user_id": DANAE_UID,
            "score_big5_estroversione": 0.65625, "score_big5_gradevolezza": 0.625, "score_big5_coscienziosita": 0.6875,
            "score_big5_nevroticismo": 0.25, "score_big5_apertura": 0.75,
            "confidenza_big5_estroversione": 1.0, "confidenza_big5_gradevolezza": 1.0,
            "confidenza_big5_coscienziosita": 1.0, "confidenza_big5_nevroticismo": 1.0, "confidenza_big5_apertura": 1.0,
            # stile_attaccamento RIMOSSO (v. CLAUDE.md 2026-09-06).
            "ansia_score": 0.41666666, "evitamento_score": 0.3888889,
            "confidenza_attaccamento_ansia": 1.0, "confidenza_attaccamento_evitamento": 0.6,
            "eq_pilastro_autoconsapevolezza": 0.45833334, "eq_pilastro_autoregolazione": 0.625,
            "eq_pilastro_empatia": 0.5416667, "eq_pilastro_responsabilita": 0.45833334, "score_maturita_emotiva": 0.5208334,
            "confidenza_eq_autoconsapevolezza": 1.0, "confidenza_eq_autoregolazione": 1.0,
            "confidenza_eq_empatia": 1.0, "confidenza_eq_responsabilita": 1.0,
            "confidenza_eq_autoregolazione_interna": 1.0, "confidenza_eq_empatia_interna": 1.0,
            "flag_profilo_per_revisione_dati": False, "flag_trappola_fallita": 0,
            "profilo_valori_self": {"bisogno_stabilita": 0.75, "crescita_personale": 0.75, "centralita_famiglia": 1.0, "orientamento_carriera": 0.75},
            "profilo_valori_partner_ideale": {"bisogno_stabilita": 0.75, "crescita_personale": 0.75, "centralita_famiglia": 0.75, "orientamento_carriera": 0.75},
            "profilo_stile_vita_self": {"socialita": 0.75, "ritmo_vita": 0.75, "organizzazione": 0.5},
            "profilo_stile_vita_partner_ideale": {"socialita": 0.75, "ritmo_vita": 0.75, "organizzazione": 0.5},
            "profilo_dinamica_relazionale_self": {"autonomia_fusione": 0.75, "condivisione_ruoli": 0.75, "espressivita_emotiva": 1.0},
            "profilo_dinamica_relazionale_partner_ideale": {"autonomia_fusione": 0.75, "condivisione_ruoli": 1.0, "espressivita_emotiva": 1.0},
            "profilo_aspirazioni_self": {"mobilita_geografica": 0.5, "impegno_lungo_termine": 0.75, "orizzonte_progettuale": 0.5},
            "profilo_aspirazioni_partner_ideale": {"mobilita_geografica": 0.5, "impegno_lungo_termine": 0.75, "orizzonte_progettuale": 0.5},
        },
        "interest_tags": {
            # Contenuto di prova evidente (v. nota in cima al file) —
            # riprodotto fedelmente, non riscritto.
            "user_id": DANAE_UID,
            "mi_piace": "Qui dovresti poter selezionare cose in base alle categorie", "non_sopporto": "Xvg",
            "partner_vorrei": "Hj", "partner_non_vorrei": "Zdf",
            "mi_piace_tags": ["qui dovresti poter selezionare cose in base alle categorie"],
            "non_sopporto_tags": ["xvg"], "partner_vorrei_tags": ["hj"], "partner_non_vorrei_tags": ["zdf"],
        },
        "profile_narrative": {
            "user_id": DANAE_UID,
            "descrizione_di_se": "Sono iooo",
            "descrizione_partner_ideale": "Sempre iooo ahah",
        },
    },
]

# uuid[] — cast esplicito richiesto (v. CLAUDE.md: psycopg2 adatta di
# default una lista Python di stringhe a text[], non uuid[]).
MATCHES = [
    {
        "match": {
            "match_id": ALBERTO_MATCH_ID, "user_a_id": ALBERTO_UID, "user_b_id": PATRIZIA_UID, "stato": "Confermato",
            "data_proposta": "2026-09-01 20:02:38.191236+00:00", "data_scadenza_risposta": "2026-09-08 20:02:45.142264+00:00",
            "data_conferma": "2026-09-01 20:07:02.219864+00:00",
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
        },
        "shortlist_candidati": [PATRIZIA_UID, "59730b3d-57c0-4bb8-ae87-867bbc6a98c1"],
    },
    {
        "match": {
            # Match reale creato il 2026-09-05 (v. CLAUDE.md) per verificare il
            # fix lingue_parlate — stato 'Proposto' (non ancora accettato da
            # nessuna delle due parti), riprodotto così com'è.
            "match_id": DANAE_MATCH_ID, "user_a_id": DANAE_UID, "user_b_id": SEBASTIAN_UID, "stato": "Proposto",
            "data_proposta": "2026-09-05 11:02:14.602356+00:00", "data_scadenza_risposta": "2026-09-12 11:02:24.102500+00:00",
            "data_conferma": None,
            "final_score": 0.6360597, "pagamento_a_stato": None, "pagamento_b_stato": None,
            "contatto_scambiato": False, "selezionato_per_somiglianza_visiva": False,
            "flag_rifiuto_esplicito": False, "flag_asimmetria_narrativa": False, "algoritmo_versione": "stable_v9",
            "algoritmo_parametri": {
                "weight_bigfive": 0.3, "weight_narrativa": 0.2, "weight_eq_empatia": 0.25,
                "jwt_scadenza_giorni": 30.0, "otp_scadenza_minuti": 10.0, "otp_tentativi_massimi": 5.0,
                "report_top_candidates": 10.0, "soglia_area_urbana_km": 50.0,
                "cadenza_giorni_pillola": 2.0, "soglia_minima_proposta": 0.55, "weight_eq_attaccamento": 0.35,
                "weight_preferenze_soft": 0.15, "mesi_esclusione_rimatch": 6.0, "fee_match_confermato_eur": 15.0,
                "weight_eq_responsabilita": 0.25, "otp_rate_limit_ip_per_ora": 10.0, "weight_eq_autoregolazione": 0.25,
                "recupero_accesso_grazia_ore": 48.0, "weight_eq_autoconsapevolezza": 0.25,
                "finestra_risposta_match_giorni": 7.0, "otp_richiesta_cooldown_secondi": 60.0,
                "cadenza_email_engagement_giorni": 7.0, "giorno_esecuzione_ciclo_mensile": 1.0,
                "soglia_similarita_visiva_minima": 0.2, "cadenza_giorni_ricalcolo_profilo": 60.0,
                "cadenza_giorni_proposta_abbinamento": 30.0, "dimensione_shortlist_analisi_visiva": 5.0,
                "soglia_percentile_similarita_visiva": 0.9, "cadenza_giorni_domanda_approfondimento": 7.0,
                "soglia_importanza_vicinanza_esclusione": 0.6,
            },
            "analisi_caratteriale_coppia": (
                "Il vostro abbinamento nasce da alcune affinità concrete, insieme a un'area su cui vale "
                "la pena costruire dialogo fin da subito.\n\nCosa vi avvicina:\n"
                "• Apertura mentale — Condividete una spiccata curiosità verso il mondo e le nuove "
                "esperienze, capace di mantenere sempre vivi gli stimoli intellettuali e le conversazioni "
                "tra voi.\n"
                "• Stile relazionale — Mostrate entrambi una solida base di sicurezza emotiva, che "
                "permette di affrontare i legami affettivi con stabilità e serenità reciproca.\n"
                "• Gradevolezza — Vivete le relazioni con un fondo comune di empatia e attenzione per "
                "l'altro, rendendo naturale un clima di cura e rispetto quotidiano.\n\n"
                "Su cosa vale la pena dialogare:\n"
                "• Gestione emotiva — Di fronte alle tensioni quotidiane potreste sperimentare livelli "
                "diversi di reattività emotiva, rendendo prezioso uno spazio di ascolto per accogliere i "
                "diversi modi di vivere il carico di stress."
            ),
        },
        "shortlist_candidati": [
            SEBASTIAN_UID, "e38e2ee3-c610-47d3-80b5-ff10e1d10532", "ebfff88c-ce3a-47ed-b38b-d9ec84d1e093",
            "bb4d6344-8b0e-4ae5-9c1b-a3fc5a63f81f", "9375163c-7918-4b75-a9af-7590d61683f2",
        ],
    },
]


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


def _upsert_socio_profile(cur, dati):
    # coordinate_gps è un tipo point, non esprimibile con l'helper generico
    # _upsert() sopra (richiede point(%s, %s), non un singolo placeholder) —
    # stesso pattern già usato in routers/profile.py per lo stesso campo.
    socio = dict(dati)
    lon, lat = socio.pop("lon"), socio.pop("lat")
    colonne = list(socio.keys())
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in colonne if c != "user_id")
    cur.execute(
        f"""
        INSERT INTO socio_profile ({', '.join(colonne)}, coordinate_gps)
        VALUES ({', '.join(['%s'] * len(colonne))}, point(%s, %s))
        ON CONFLICT (user_id) DO UPDATE SET {set_clause}, coordinate_gps = point(%s, %s)
        """,
        [socio[c] for c in colonne] + [lon, lat, lon, lat],
    )


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

    for persona in PERSONE:
        u = persona["users"]
        # Stub di registrazione abbandonata con la stessa email, user_id
        # diverso (nome/cognome mai compilati) — rimosso prima, altrimenti
        # il vincolo UNIQUE su users.email fa fallire l'upsert (già
        # capitato per Alberto).
        cur.execute(
            "DELETE FROM users WHERE email = %s AND user_id != %s AND nome IS NULL",
            (u["email"], u["user_id"]),
        )
        if cur.rowcount:
            print(f"Rimosso {cur.rowcount} stub di registrazione abbandonata per {u['email']}.")

        # users e physical_profile PRIMA di tutto il resto — ogni altra
        # tabella satellite ha una FK su user_id, l'ordine qui non è
        # arbitrario (trovato dal vivo: un primo tentativo con
        # socio_profile prima ha violato la FK).
        _upsert(cur, "users", u)
        _upsert(cur, "physical_profile", persona["physical_profile"])
        _upsert_socio_profile(cur, persona["socio_profile"])
        _upsert(cur, "dealbreaker_criteria", persona["dealbreaker_criteria"])
        _upsert(cur, "soft_criteria", persona["soft_criteria"])
        _upsert(cur, "psychometric_scores", persona["psychometric_scores"])
        _upsert(cur, "interest_tags", persona["interest_tags"])
        _upsert(cur, "profile_narrative", persona["profile_narrative"])
        print(f"Fixture '{u['nome']} {u['cognome']}' ({u['email']}): inserita/aggiornata.")

    # I match dipendono da profili demo (Patrizia/Sebastian) già garantiti
    # dal seed del pool demo con lo stesso user_id, quindi la FK qui sotto
    # è sicura anche su un DB appena riseedato in quest'ordine (demo pool
    # prima, poi questo script).
    for voce in MATCHES:
        _upsert(cur, "matches", voce["match"], pk="match_id")
        # shortlist_candidati (uuid[]) a parte, stesso motivo di
        # coordinate_gps sopra — non esprimibile con l'helper generico.
        cur.execute(
            "UPDATE matches SET shortlist_candidati = %s::uuid[] WHERE match_id = %s",
            (voce["shortlist_candidati"], voce["match"]["match_id"]),
        )
        print(f"Match {voce['match']['match_id']} ({voce['match']['stato']}): inserito/aggiornato.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
