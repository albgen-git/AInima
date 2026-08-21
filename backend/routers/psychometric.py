"""RF-07/RF-07b: test psicometrici scritti (Big Five, Attaccamento, EQ
Score — tutti a scoring deterministico) + i due campi liberi che
alimentano solo il layer generativo (Prompt 3a/3b + embedding testuale).

Aggiornamento 2026-08-19 (v. CLAUDE.md): la chat-intervista EQ (Prompt 1/2,
Gemini) non è più nel flusso attivo, sostituita dai test scritti sotto —
l'endpoint resta nel codice ma DISATTIVATO dietro CHAT_INTERVISTA_ATTIVA,
non cancellato (potrebbe tornare utile in futuro, v. istruzione utente)."""

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.psychometric import (
    AttaccamentoResult, AttaccamentoSubmission, BigFiveResult, BigFiveSubmission,
    ChatMessageIn, ChatMessageOut, EqResult, EqSubmission, NarrativeUpdate,
    REVERSE_ITEMS, REVERSE_ITEMS_ATTACCAMENTO, REVERSE_ITEMS_EQ,
)
from services import llm_pipeline, text_embedding

router = APIRouter(prefix="/users/{user_id}", tags=["psychometric"])

# v. nota in cima al file — disattivato ma non cancellato.
CHAT_INTERVISTA_ATTIVA = False

DIMENSIONI = {
    "estroversione": "E", "gradevolezza": "A", "coscienziosita": "C",
    "nevroticismo": "N", "apertura": "O",
}


def _config_float(cur, chiave: str, default: float) -> float:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return float(r["valore"]) if r else default


def calcola_big_five(risposte: dict) -> BigFiveResult:
    punteggi = {}
    for dimensione, prefisso in DIMENSIONI.items():
        totale = 0
        for i in range(1, 9):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            ricodificato = 6 - grezzo if codice in REVERSE_ITEMS else grezzo
            totale += ricodificato
        media = totale / 8
        punteggi[f"score_big5_{dimensione}"] = (media - 1) / 4  # normalizzato 0.0-1.0
    return BigFiveResult(**punteggi)


def calcola_attaccamento(risposte: dict) -> AttaccamentoResult:
    """Ainima_Test_Attaccamento_v1.md §5. ansia_score/evitamento_score sono
    il dato primario; stile_attaccamento è derivato SOLO per la UI."""
    def _media(prefisso):
        totale = 0
        for i in range(1, 13):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            ricodificato = 6 - grezzo if codice in REVERSE_ITEMS_ATTACCAMENTO else grezzo
            totale += ricodificato
        return totale / 12

    ansia_score = (_media("AN") - 1) / 4
    evitamento_score = (_media("EV") - 1) / 4

    if ansia_score < 0.5 and evitamento_score < 0.5:
        stile = "Sicuro"
    elif ansia_score >= 0.5 and evitamento_score < 0.5:
        stile = "Ansioso"
    elif ansia_score < 0.5 and evitamento_score >= 0.5:
        stile = "Evitante"
    else:
        stile = "Timoroso/Disorganizzato"

    return AttaccamentoResult(ansia_score=ansia_score, evitamento_score=evitamento_score, stile_attaccamento=stile)


def calcola_eq(risposte: dict, cur) -> EqResult:
    """Ainima_Test_EQScore_v1.md §3. I pesi dei 4 pilastri in
    score_maturita_emotiva sono configurabili da admin console (default
    equi), mai hardcoded."""
    pilastri = {"autoconsapevolezza": "AC", "autoregolazione": "AR", "empatia": "EM", "responsabilita": "RE"}
    punteggi = {}
    for nome, prefisso in pilastri.items():
        totale = 0
        for i in range(1, 9):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            ricodificato = 6 - grezzo if codice in REVERSE_ITEMS_EQ else grezzo
            totale += ricodificato
        media = totale / 8
        punteggi[f"eq_pilastro_{nome}"] = (media - 1) / 4

    pesi = {
        "autoconsapevolezza": _config_float(cur, "weight_eq_autoconsapevolezza", 0.25),
        "autoregolazione": _config_float(cur, "weight_eq_autoregolazione", 0.25),
        "empatia": _config_float(cur, "weight_eq_empatia", 0.25),
        "responsabilita": _config_float(cur, "weight_eq_responsabilita", 0.25),
    }
    maturita = sum(punteggi[f"eq_pilastro_{nome}"] * peso for nome, peso in pesi.items())

    return EqResult(**punteggi, score_maturita_emotiva=maturita)


def _ricalcola_flag_revisione_dati(cur, user_id: UUID):
    """Ainima_Test_EQScore_v1.md §4 (incoerenza statistica Big Five/EQ,
    puro confronto numerico, zero LLM) + Ainima_Algoritmo_Ranking_Finale_v1.md
    §10 (quadrante Timoroso/Disorganizzato) — ricalcolata per intero ad ogni
    submission, non solo aggiunta, così il flag riflette sempre lo stato
    corrente dei dati disponibili."""
    cur.execute("""
        SELECT score_big5_nevroticismo, score_big5_gradevolezza, score_big5_coscienziosita,
               eq_pilastro_autoregolazione, eq_pilastro_empatia,
               ansia_score, evitamento_score
        FROM psychometric_scores WHERE user_id = %s
    """, (str(user_id),))
    r = cur.fetchone()
    if not r:
        return

    n_incoerenze = 0
    if r["score_big5_nevroticismo"] is not None and r["eq_pilastro_autoregolazione"] is not None:
        if abs(r["score_big5_nevroticismo"] - (1 - r["eq_pilastro_autoregolazione"])) > 0.5:
            n_incoerenze += 1
        if r["score_big5_coscienziosita"] is not None and \
                abs(r["score_big5_coscienziosita"] - r["eq_pilastro_autoregolazione"]) > 0.5:
            n_incoerenze += 1
    if r["score_big5_gradevolezza"] is not None and r["eq_pilastro_empatia"] is not None:
        if abs((1 - r["score_big5_gradevolezza"]) - (1 - r["eq_pilastro_empatia"])) > 0.5:
            n_incoerenze += 1

    quadrante_timoroso = (
        r["ansia_score"] is not None and r["evitamento_score"] is not None and
        r["ansia_score"] > 0.7 and r["evitamento_score"] > 0.7
    )

    flag = n_incoerenze >= 2 or quadrante_timoroso
    cur.execute("UPDATE psychometric_scores SET flag_profilo_per_revisione_dati = %s WHERE user_id = %s",
                (flag, str(user_id)))


@router.post("/bigfive", response_model=BigFiveResult)
def submit_big_five(user_id: UUID, payload: BigFiveSubmission):
    risultato = calcola_big_five(payload.risposte)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE psychometric_scores SET
            score_big5_estroversione = %s, score_big5_gradevolezza = %s,
            score_big5_coscienziosita = %s, score_big5_nevroticismo = %s,
            score_big5_apertura = %s
        WHERE user_id = %s
    """, (
        risultato.score_big5_estroversione, risultato.score_big5_gradevolezza,
        risultato.score_big5_coscienziosita, risultato.score_big5_nevroticismo,
        risultato.score_big5_apertura, str(user_id),
    ))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    _ricalcola_flag_revisione_dati(cur, user_id)
    conn.commit()
    conn.close()
    return risultato


@router.post("/attaccamento", response_model=AttaccamentoResult)
def submit_attaccamento(user_id: UUID, payload: AttaccamentoSubmission):
    """Ainima_Test_Attaccamento_v1.md — 24 item, sostituisce la distribuzione
    a 4 stili prima dedotta dalla chat-intervista LLM."""
    risultato = calcola_attaccamento(payload.risposte)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE psychometric_scores SET ansia_score = %s, evitamento_score = %s, stile_attaccamento = %s
        WHERE user_id = %s
    """, (risultato.ansia_score, risultato.evitamento_score, risultato.stile_attaccamento, str(user_id)))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    _ricalcola_flag_revisione_dati(cur, user_id)
    conn.commit()
    conn.close()
    return risultato


@router.post("/eq", response_model=EqResult)
def submit_eq(user_id: UUID, payload: EqSubmission):
    """Ainima_Test_EQScore_v1.md — 32 item, sostituisce il rubric-scorer LLM
    (Prompt 2) sulla chat-intervista."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM psychometric_scores WHERE user_id = %s", (str(user_id),))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    risultato = calcola_eq(payload.risposte, cur)
    cur.execute("""
        UPDATE psychometric_scores SET
            eq_pilastro_autoconsapevolezza = %s, eq_pilastro_autoregolazione = %s,
            eq_pilastro_empatia = %s, eq_pilastro_responsabilita = %s,
            score_maturita_emotiva = %s
        WHERE user_id = %s
    """, (
        risultato.eq_pilastro_autoconsapevolezza, risultato.eq_pilastro_autoregolazione,
        risultato.eq_pilastro_empatia, risultato.eq_pilastro_responsabilita,
        risultato.score_maturita_emotiva, str(user_id),
    ))
    _ricalcola_flag_revisione_dati(cur, user_id)
    conn.commit()
    conn.close()
    return risultato


@router.put("/narrative")
def aggiorna_narrative(user_id: UUID, payload: NarrativeUpdate):
    """RF-07b: i due campi liberi "Descrivi te stesso"/"Descrivi il tuo
    partner ideale". Ognuno, se presente, alimenta SOLO Prompt 3a/3b
    (trasformazione singola stateless, non una conversazione) + l'embedding
    testuale (services/text_embedding.py) — mai direttamente lo score di
    compatibilità (RNF-11)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id = %s", (str(user_id),))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    campi = {}
    if payload.descrizione_di_se is not None:
        campi["descrizione_di_se"] = payload.descrizione_di_se
    if payload.descrizione_partner_ideale is not None:
        campi["descrizione_partner_ideale"] = payload.descrizione_partner_ideale
    if campi:
        set_clause = ", ".join(f"{k} = %s" for k in campi)
        cur.execute(f"""
            INSERT INTO profile_narrative (user_id, {', '.join(campi)}, data_ultima_modifica)
            VALUES (%s, {', '.join(['%s'] * len(campi))}, now())
            ON CONFLICT (user_id) DO UPDATE SET {set_clause}, data_ultima_modifica = now()
        """, (str(user_id), *campi.values(), *campi.values()))

    if payload.descrizione_di_se:
        canonico = llm_pipeline.estrai_profilo_self(payload.descrizione_di_se)
        embedding = text_embedding.embed_testo(canonico)
        cur.execute("""
            UPDATE psychometric_scores SET self_profile_canonico = %s, self_embedding_vector = %s
            WHERE user_id = %s
        """, (canonico, embedding, str(user_id)))

    if payload.descrizione_partner_ideale:
        canonico = llm_pipeline.estrai_profilo_ideale(payload.descrizione_partner_ideale)
        embedding = text_embedding.embed_testo(canonico)
        cur.execute("""
            UPDATE psychometric_scores SET ideal_partner_profile_canonico = %s, ideal_embedding_vector = %s
            WHERE user_id = %s
        """, (canonico, embedding, str(user_id)))

    conn.commit()
    conn.close()
    return {"aggiornato": True}


@router.post("/chat/message", response_model=ChatMessageOut)
def invia_messaggio_chat(user_id: UUID, payload: ChatMessageIn):
    """Prompt 1 (IA Intervistatrice) — DISATTIVATO, v. CHAT_INTERVISTA_ATTIVA
    in cima al file. Sostituito dai test scritti /attaccamento e /eq sopra."""
    if not CHAT_INTERVISTA_ATTIVA:
        raise HTTPException(410, "Chat-intervista non più attiva — sostituita dai test scritti (RF-07)")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT chat_transcript, chat_eq_completata_il FROM psychometric_scores WHERE user_id = %s
    """, (str(user_id),))
    riga = cur.fetchone()
    if riga is None:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    if riga["chat_eq_completata_il"] is not None:
        conn.close()
        raise HTTPException(409, "Chat-intervista già completata per questo utente")

    transcript = riga["chat_transcript"] or []
    if payload.testo:
        transcript.append({"ruolo": "utente", "testo": payload.testo})
    esito = llm_pipeline.intervista_rispondi(transcript)
    transcript.append({"ruolo": "assistente", "testo": esito["testo"]})
    cur.execute("UPDATE psychometric_scores SET chat_transcript = %s::jsonb WHERE user_id = %s",
                (json.dumps(transcript), str(user_id)))
    conn.commit()
    conn.close()
    return ChatMessageOut(testo=esito["testo"], conversazione_completata=esito["conversazione_completata"])


@router.get("/report")
def report_prontezza_relazionale(user_id: UUID):
    """RF: 'La tua Prontezza Relazionale' — richiede il Prompt 5 via LLM.
    Ritorna il testo salvato se già generato, altrimenti un placeholder."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT report_prontezza_relazionale FROM psychometric_scores WHERE user_id = %s", (str(user_id),))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(404, "Utente non trovato")
    testo = row["report_prontezza_relazionale"]
    if testo is None:
        return {"pronto": False, "testo": None}
    return {"pronto": True, "testo": testo}
