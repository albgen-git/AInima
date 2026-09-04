"""RF-25h: esportazione consolidata delle risposte di onboarding di un
utente in un unico file JSON, salvato su R2 nello stesso "spazio" già
usato per le sue foto — pensato per debug/supporto senza dover incrociare
manualmente users/physical_profile/socio_profile/dealbreaker_criteria/
soft_criteria/psychometric_scores/interest_tags/profile_narrative (v.
CLAUDE.md — non esiste nessun log/file consolidato preesistente, verificato
con una ricerca in tutto backend/ e scripts/ prima di scrivere questo).

Modulo condiviso tra scripts/export_onboarding_json.py (CLI, uso manuale
su richiesta) e routers/auth.py (trigger automatico al completamento
dell'onboarding, v. CLAUDE.md — richiesta esplicita dell'utente: "da
adesso tutti i nuovi utenti che completano l'onboarding dovranno avere il
file log delle risposte fornite"). Stessa funzione, mai due implementazioni
parallele — coerente con il principio già seguito per matching_engine.py.

IMPORTANTE — cosa NON contiene: le "risposte" ai quattro test psicometrici
sono i punteggi già AGGREGATI (score_big5_*, ansia_score/evitamento_score,
eq_pilastro_*, le 13 sotto-dimensioni del Profilo Relazionale) — mai le
risposte item-per-item ai singoli quesiti del questionario, che questo
sistema non persiste MAI da nessuna parte per principio architetturale
(RNF-11, ripetuto in più moduli: services/personal_report.py,
services/llm_pipeline.py, services/engagement.py). Non è un'omissione di
questo modulo, è un dato che semplicemente non esiste nel DB.

Esclude esplicitamente metodo_pagamento_token (nessun token di pagamento
nell'export) — l'autenticazione è via OTP email, non esiste alcun
password_hash da escludere (rimosso dallo schema con la migrazione RF-02b).
"""

import json
import os
from datetime import datetime, timezone

# Escluso esplicitamente dall'export (richiesta utente + principio generale
# di non includere mai token di pagamento in un dump di debug).
USERS_CAMPI_ESCLUSI = {"metodo_pagamento_token"}


def _riga(cur, tabella: str, user_id: str, escludi: set[str] = frozenset()) -> dict:
    cur.execute(f"SELECT * FROM {tabella} WHERE user_id = %s", (user_id,))
    riga = cur.fetchone()
    if not riga:
        return {}
    return {k: v for k, v in dict(riga).items() if k not in escludi}


def costruisci_export(cur, user_id: str) -> dict:
    u = _riga(cur, "users", user_id, USERS_CAMPI_ESCLUSI)
    p = _riga(cur, "physical_profile", user_id)
    s = _riga(cur, "socio_profile", user_id)
    d = _riga(cur, "dealbreaker_criteria", user_id)
    soft = _riga(cur, "soft_criteria", user_id)
    ps = _riga(cur, "psychometric_scores", user_id)
    tags = _riga(cur, "interest_tags", user_id)
    narr = _riga(cur, "profile_narrative", user_id)

    # coordinate_gps (tipo point di Postgres) arriva da psycopg2 come
    # stringa grezza "(lon,lat)", non come tupla — psycopg2 non ha un
    # adattatore nativo per point (v. matching_engine.load_pool(), che per
    # lo stesso motivo lo estrae via SQL con coordinate_gps[0]/[1] invece
    # di affidarsi al valore Python). Un primo tentativo indicizzava i
    # caratteri della stringa ("(", "9") invece di parsarla — trovato
    # subito controllando l'estratto reale, non assunto corretto.
    coord = s.pop("coordinate_gps", None)
    if coord is not None:
        lon_str, lat_str = coord.strip("()").split(",")
        s["coordinate_gps"] = {"lon": float(lon_str), "lat": float(lat_str)}

    return {
        "user_id": user_id,
        "generato_il": datetime.now(timezone.utc).isoformat(),
        "anagrafico_fisico_socioeconomico": {
            "users": u,
            "physical_profile": p,
            "socio_profile": s,
        },
        "criteri_ricerca": {
            "dealbreaker": d,
            "soft": soft,
        },
        "test_psicometrici": {
            "nota": (
                "Contiene solo i punteggi già aggregati per ciascun test — le "
                "risposte item-per-item ai singoli quesiti non sono mai "
                "persistite in questo sistema (principio architetturale "
                "RNF-11), quindi non possono comparire in questo export."
            ),
            "big_five": {
                "score_big5_estroversione": ps.get("score_big5_estroversione"),
                "score_big5_gradevolezza": ps.get("score_big5_gradevolezza"),
                "score_big5_coscienziosita": ps.get("score_big5_coscienziosita"),
                "score_big5_nevroticismo": ps.get("score_big5_nevroticismo"),
                "score_big5_apertura": ps.get("score_big5_apertura"),
                "confidenza_big5_estroversione": ps.get("confidenza_big5_estroversione"),
                "confidenza_big5_gradevolezza": ps.get("confidenza_big5_gradevolezza"),
                "confidenza_big5_coscienziosita": ps.get("confidenza_big5_coscienziosita"),
                "confidenza_big5_nevroticismo": ps.get("confidenza_big5_nevroticismo"),
                "confidenza_big5_apertura": ps.get("confidenza_big5_apertura"),
            },
            "attaccamento": {
                "ansia_score": ps.get("ansia_score"),
                "evitamento_score": ps.get("evitamento_score"),
                "stile_attaccamento": ps.get("stile_attaccamento"),
                "confidenza_attaccamento_ansia": ps.get("confidenza_attaccamento_ansia"),
                "confidenza_attaccamento_evitamento": ps.get("confidenza_attaccamento_evitamento"),
            },
            "eq": {
                "eq_pilastro_autoconsapevolezza": ps.get("eq_pilastro_autoconsapevolezza"),
                "eq_pilastro_autoregolazione": ps.get("eq_pilastro_autoregolazione"),
                "eq_pilastro_empatia": ps.get("eq_pilastro_empatia"),
                "eq_pilastro_responsabilita": ps.get("eq_pilastro_responsabilita"),
                "score_maturita_emotiva": ps.get("score_maturita_emotiva"),
                "confidenza_eq_autoconsapevolezza": ps.get("confidenza_eq_autoconsapevolezza"),
                "confidenza_eq_autoregolazione": ps.get("confidenza_eq_autoregolazione"),
                "confidenza_eq_empatia": ps.get("confidenza_eq_empatia"),
                "confidenza_eq_responsabilita": ps.get("confidenza_eq_responsabilita"),
            },
            "profilo_relazionale": {
                "valori_self": ps.get("profilo_valori_self"),
                "valori_partner_ideale": ps.get("profilo_valori_partner_ideale"),
                "stile_vita_self": ps.get("profilo_stile_vita_self"),
                "stile_vita_partner_ideale": ps.get("profilo_stile_vita_partner_ideale"),
                "dinamica_relazionale_self": ps.get("profilo_dinamica_relazionale_self"),
                "dinamica_relazionale_partner_ideale": ps.get("profilo_dinamica_relazionale_partner_ideale"),
                "aspirazioni_self": ps.get("profilo_aspirazioni_self"),
                "aspirazioni_partner_ideale": ps.get("profilo_aspirazioni_partner_ideale"),
            },
            "indicatori_qualita_dato": {
                "flag_profilo_per_revisione_dati": ps.get("flag_profilo_per_revisione_dati"),
                "flag_trappola_fallita": ps.get("flag_trappola_fallita"),
            },
        },
        "narrativa_libera": {
            "descrizione_di_se": narr.get("descrizione_di_se"),
            "descrizione_partner_ideale": narr.get("descrizione_partner_ideale"),
        },
        "liste_piace_non_sopporto": {
            "mi_piace": tags.get("mi_piace"),
            "non_sopporto": tags.get("non_sopporto"),
            "partner_vorrei": tags.get("partner_vorrei"),
            "partner_non_vorrei": tags.get("partner_non_vorrei"),
            "mi_piace_tags": tags.get("mi_piace_tags"),
            "non_sopporto_tags": tags.get("non_sopporto_tags"),
            "partner_vorrei_tags": tags.get("partner_vorrei_tags"),
            "partner_non_vorrei_tags": tags.get("partner_non_vorrei_tags"),
        },
    }


def trova_campi_mancanti(export: dict) -> list[str]:
    """Elenco a piatto "sezione.campo" per ogni valore None/vuoto/dict vuoto
    trovato — utile per il troubleshooting."""
    mancanti = []

    def _visita(prefix, valore):
        if isinstance(valore, dict):
            if not valore:
                mancanti.append(prefix)
                return
            for k, v in valore.items():
                _visita(f"{prefix}.{k}" if prefix else k, v)
        elif valore is None:
            mancanti.append(prefix)

    for sezione, contenuto in export.items():
        if sezione in ("user_id", "generato_il"):
            continue
        _visita(sezione, contenuto)
    return mancanti


def upload_r2(user_id: str, contenuto: dict) -> str:
    import boto3

    bucket = os.environ["R2_BUCKET_NAME"]
    public_base = os.environ["R2_PUBLIC_BASE_URL"].rstrip("/")
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    # Stessa convenzione di services/photo_storage.py::R2PhotoStorage.salva()
    # ("{sottocartella}/{user_id}{estensione}") — sottocartella dedicata
    # invece di "profilo"/"partner_ideale", stesso schema di naming.
    chiave = f"onboarding-export/{user_id}.json"
    corpo = json.dumps(contenuto, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    client.put_object(Bucket=bucket, Key=chiave, Body=corpo, ContentType="application/json")
    return f"{public_base}/{chiave}"


def genera_e_carica(cur, user_id: str) -> str:
    """Comodità per il chiamante automatico (routers/auth.py): costruisce
    + carica in un solo passo, ritorna l'URL pubblico."""
    export = costruisci_export(cur, user_id)
    return upload_r2(user_id, export)
