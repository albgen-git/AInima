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
    PREFISSO_CATEGORIA_PROFILO_RELAZIONALE, ProfiloRelazionaleResult, ProfiloRelazionaleSubmission,
    SOTTODIMENSIONI_PROFILO_RELAZIONALE,
    REVERSE_ITEMS, REVERSE_ITEMS_ATTACCAMENTO, REVERSE_ITEMS_EQ, TRAPPOLA_RISPOSTA_ATTESA,
)
from services import llm_pipeline, personal_report, text_embedding

router = APIRouter(prefix="/users/{user_id}", tags=["psychometric"])

# v. nota in cima al file — disattivato ma non cancellato.
CHAT_INTERVISTA_ATTIVA = False

# 2026-08-21 (v. CLAUDE.md — dopo il Blocco D): Prompt 3a/3b (estrazione
# profilo canonico) + l'embedding testuale sono stati trovati orfani —
# scrivono self_profile_canonico/ideal_partner_profile_canonico/
# self_embedding_vector/ideal_embedding_vector, ma NESSUN codice li rilegge
# oggi (Prompt 5, il generatore del report che dovrebbe consumarli, non è
# mai stato implementato — solo un endpoint stub che legge una colonna che
# nessuno scrive). In pausa per non continuare a pagare chiamate LLM/
# embedding reali per un output che nessuno usa — riattivare insieme
# all'implementazione di Prompt 5, non prima. I due campi liberi
# (descrizione_di_se/descrizione_partner_ideale) continuano a salvarsi
# normalmente: solo la trasformazione derivata è sospesa.
GENERAZIONE_PROFILO_CANONICO_ATTIVA = False

def _tenta_report_personale(conn, cur, user_id: UUID):
    """RF-28/30b: dopo ogni submission di uno dei 4 test, prova a generare
    il report di analisi personale (services/personal_report.py decide da
    solo se tutti e 4 sono ormai completi — no-op altrimenti). Avvolto qui,
    non dentro services/personal_report.py: un fallimento (LLM lento/non
    disponibile) non deve mai far fallire la submission del test, che è
    già stata committata prima di questa chiamata."""
    try:
        personal_report.genera_e_salva(conn, cur, user_id)
    except Exception as e:
        print(f"[ERRORE] generazione report personale per {user_id} fallita: {e}")


DIMENSIONI = {
    "estroversione": "E", "gradevolezza": "A", "coscienziosita": "C",
    "nevroticismo": "N", "apertura": "O",
}


def _config_float(cur, chiave: str, default: float) -> float:
    cur.execute("SELECT valore FROM system_config WHERE chiave = %s", (chiave,))
    r = cur.fetchone()
    return float(r["valore"]) if r else default


def calcola_big_five(risposte: dict) -> tuple[BigFiveResult, dict]:
    """Ritorna (punteggi, confidenza) — confidenza[dimensione] = 0.6 se il
    range interno (max-min dei punteggi ricodificati degli 8 item) è >= 3.5,
    altrimenti 1.0 (Ainima_Test_Psicometrico_BigFive_v1.md §7 Step 4). Serve
    i punteggi ricodificati grezzi, quindi va calcolata qui — non è
    recuperabile in un secondo momento dai soli score_big5_* già aggregati."""
    punteggi = {}
    confidenza = {}
    for dimensione, prefisso in DIMENSIONI.items():
        ricodificati = []
        for i in range(1, 9):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            ricodificato = 6 - grezzo if codice in REVERSE_ITEMS else grezzo
            ricodificati.append(ricodificato)
        media = sum(ricodificati) / 8
        punteggi[f"score_big5_{dimensione}"] = (media - 1) / 4  # normalizzato 0.0-1.0

        range_dimensione = max(ricodificati) - min(ricodificati)
        confidenza[f"confidenza_big5_{dimensione}"] = 0.6 if range_dimensione >= 3.5 else 1.0
    return BigFiveResult(**punteggi), confidenza


def calcola_attaccamento(risposte: dict) -> tuple[AttaccamentoResult, dict]:
    """Ainima_Test_Attaccamento_v1.md §5. ansia_score/evitamento_score sono
    il dato primario; stile_attaccamento è derivato SOLO per la UI.

    Ritorna anche (Blocco C, seconda passata — §5 Step 3bis) la confidenza
    per le 2 dimensioni: stessa identica formula del Big Five (range >= 3.5
    sui punteggi ricodificati), nessun controllo incrociato con altri test —
    a differenza di Autoregolazione/Empatia nell'EQ, qui non serve una
    coppia di colonne "_interna", il valore è già finale."""
    def _ricodificati(prefisso):
        vals = []
        for i in range(1, 10):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            vals.append(6 - grezzo if codice in REVERSE_ITEMS_ATTACCAMENTO else grezzo)
        return vals

    ricodificati_ansia = _ricodificati("AN")
    ricodificati_evitamento = _ricodificati("EV")

    ansia_score = (sum(ricodificati_ansia) / 9 - 1) / 4
    evitamento_score = (sum(ricodificati_evitamento) / 9 - 1) / 4

    confidenza = {
        "confidenza_attaccamento_ansia":
            0.6 if (max(ricodificati_ansia) - min(ricodificati_ansia)) >= 3.5 else 1.0,
        "confidenza_attaccamento_evitamento":
            0.6 if (max(ricodificati_evitamento) - min(ricodificati_evitamento)) >= 3.5 else 1.0,
    }

    if ansia_score < 0.5 and evitamento_score < 0.5:
        stile = "Sicuro"
    elif ansia_score >= 0.5 and evitamento_score < 0.5:
        stile = "Ansioso"
    elif ansia_score < 0.5 and evitamento_score >= 0.5:
        stile = "Evitante"
    else:
        stile = "Timoroso/Disorganizzato"

    risultato = AttaccamentoResult(ansia_score=ansia_score, evitamento_score=evitamento_score, stile_attaccamento=stile)
    return risultato, confidenza


def calcola_eq(risposte: dict, cur) -> tuple[EqResult, dict]:
    """Ainima_Test_EQScore_v1.md §3 (punteggi) + §4a (varianza interna, Blocco
    C seconda passata). I pesi dei 4 pilastri in score_maturita_emotiva sono
    configurabili da admin console (default equi), mai hardcoded.

    Ritorna anche la confidenza INTERNA (solo varianza, §4a) per tutti e 4 i
    pilastri — prima Autoconsapevolezza/Responsabilità non avevano alcun
    controllo qualità. Per Autoregolazione/Empatia questo NON è ancora il
    valore pubblico finale: _ricalcola_confidenza_e_flag() applica sopra
    anche il controllo incrociato col Big Five (§4b) via min(), leggendo
    questo valore dalle colonne "_interna" (mai sovrascritte se non da qui,
    così il controllo incrociato riparte sempre da una baseline pulita)."""
    pilastri = {"autoconsapevolezza": "AC", "autoregolazione": "AR", "empatia": "EM", "responsabilita": "RE"}
    punteggi = {}
    confidenza_interna = {}
    for nome, prefisso in pilastri.items():
        ricodificati = []
        for i in range(1, 7):
            codice = f"{prefisso}{i}"
            grezzo = risposte[codice]
            ricodificato = 6 - grezzo if codice in REVERSE_ITEMS_EQ else grezzo
            ricodificati.append(ricodificato)
        media = sum(ricodificati) / 6
        punteggi[f"eq_pilastro_{nome}"] = (media - 1) / 4
        range_pilastro = max(ricodificati) - min(ricodificati)
        confidenza_interna[nome] = 0.6 if range_pilastro >= 3.5 else 1.0

    pesi = {
        "autoconsapevolezza": _config_float(cur, "weight_eq_autoconsapevolezza", 0.25),
        "autoregolazione": _config_float(cur, "weight_eq_autoregolazione", 0.25),
        "empatia": _config_float(cur, "weight_eq_empatia", 0.25),
        "responsabilita": _config_float(cur, "weight_eq_responsabilita", 0.25),
    }
    # Stima iniziale coi soli pesi base — _ricalcola_confidenza_e_flag()
    # la corregge subito dopo con la confidenza pubblica finale (submit_eq()
    # ne rilegge il valore prima di rispondere all'API).
    maturita = sum(punteggi[f"eq_pilastro_{nome}"] * peso for nome, peso in pesi.items())

    return EqResult(**punteggi, score_maturita_emotiva=maturita), confidenza_interna


def calcola_profilo_relazionale(risposte: dict) -> ProfiloRelazionaleResult:
    """Ainima_Test_Profilo_Relazionale_v1.md §6 Step 1-2. Nessun reverse,
    normalizzazione diretta (grezzo-1)/4 per ciascuno dei 26 item — a
    differenza degli altri 3 test, qui non serve una confidenza per
    dimensione (nessun controllo previsto dal documento per questo test)."""
    campi = {}
    for categoria, sottodim in SOTTODIMENSIONI_PROFILO_RELAZIONALE.items():
        prefisso = PREFISSO_CATEGORIA_PROFILO_RELAZIONALE[categoria]
        self_dict, ideale_dict = {}, {}
        for i, nome_dim in enumerate(sottodim, start=1):
            self_dict[nome_dim] = (risposte[f"{prefisso}{i}S"] - 1) / 4
            ideale_dict[nome_dim] = (risposte[f"{prefisso}{i}I"] - 1) / 4
        campi[f"profilo_{categoria}_self"] = self_dict
        campi[f"profilo_{categoria}_partner_ideale"] = ideale_dict
    return ProfiloRelazionaleResult(**campi)


def _verifica_trappola(cur, user_id: UUID, risposte: dict, codice: str):
    """Ainima_00_Indice_Schema_Consolidato_v1.md, sezione domande trappola:
    1 item di attenzione indipendente da qualunque dimensione, condiviso tra
    Big Five ('T1'), Attaccamento ('T2') ed EQ Score ('T3'). Se la risposta
    si scosta di almeno 2 punti da quella attesa (qui l'istruzione è
    esplicita, non c'è ambiguità interpretativa), incrementa il contatore
    cumulativo flag_trappola_fallita (max 3, uno per test)."""
    risposta_attesa = TRAPPOLA_RISPOSTA_ATTESA[codice]
    risposta_data = risposte[codice]
    if abs(risposta_data - risposta_attesa) >= 2:
        cur.execute(
            "UPDATE psychometric_scores SET flag_trappola_fallita = flag_trappola_fallita + 1 WHERE user_id = %s",
            (str(user_id),),
        )


def _ricalcola_confidenza_e_flag(cur, user_id: UUID):
    """Ainima_Test_EQScore_v1.md §4b (coerenza incrociata Big Five/EQ, puro
    confronto numerico, zero LLM) + Ainima_Algoritmo_Ranking_Finale_v1.md §10
    (quadrante Timoroso/Disorganizzato) + Ainima_00_Indice_Schema_Consolidato_v1.md
    (>= 1 domanda trappola fallita) — ricalcolata per intero ad ogni
    submission (Big Five/Attaccamento/EQ, in qualunque ordine arrivino), non
    solo aggiunta, così riflette sempre lo stato corrente dei dati disponibili.

    Blocco C, seconda passata (v. CLAUDE.md — correzioni di specifica, non
    solo di codice):
    - confidenza_eq_autoregolazione/empatia sono ora DERIVATE: pubblica =
      min(interna [da calcola_eq(), §4a, mai toccata qui], esito del
      controllo incrociato §4b calcolato qui sotto). Questa funzione legge
      sempre la baseline "_interna" pulita, mai il valore pubblico di un
      giro precedente — altrimenti un min() applicato sopra un valore già
      ridotto potrebbe restare bloccato a 0.6 per sempre, anche dopo che
      l'incoerenza col Big Five non sussiste più (bug evitato di proposito).
    - flag_profilo_per_revisione_dati costruisce ESPLICITAMENTE l'insieme
      deduplicato delle 11 dimensioni (5 Big Five + 4 EQ + 2 Attaccamento,
      Ainima_Algoritmo_Ranking_Finale_v1.md "Soglia per revisione umana") e
      conta quante sono == 0.6 — MAI un contatore incrementato una volta per
      ogni singolo controllo fallito (era il Bug A: due controlli incrociati
      diversi puntavano entrambi su Autoregolazione, gonfiando il conteggio
      come se fossero 2 dimensioni anomale invece di 1)."""
    cur.execute("""
        SELECT confidenza_big5_estroversione, confidenza_big5_gradevolezza,
               confidenza_big5_coscienziosita, confidenza_big5_nevroticismo, confidenza_big5_apertura,
               confidenza_attaccamento_ansia, confidenza_attaccamento_evitamento,
               confidenza_eq_autoconsapevolezza, confidenza_eq_responsabilita,
               confidenza_eq_autoregolazione_interna, confidenza_eq_empatia_interna,
               score_big5_nevroticismo, score_big5_gradevolezza, score_big5_coscienziosita,
               eq_pilastro_autoconsapevolezza, eq_pilastro_autoregolazione,
               eq_pilastro_empatia, eq_pilastro_responsabilita,
               ansia_score, evitamento_score, flag_trappola_fallita
        FROM psychometric_scores WHERE user_id = %s
    """, (str(user_id),))
    r = cur.fetchone()
    if not r:
        return

    # §4b — controllo incrociato: parte sempre dalla baseline "_interna"
    # pulita (§4a), mai dal valore pubblico di un giro precedente.
    confidenza_autoregolazione = r["confidenza_eq_autoregolazione_interna"]
    confidenza_empatia = r["confidenza_eq_empatia_interna"]
    if r["score_big5_nevroticismo"] is not None and r["eq_pilastro_autoregolazione"] is not None:
        if abs(r["score_big5_nevroticismo"] - (1 - r["eq_pilastro_autoregolazione"])) > 0.5:
            confidenza_autoregolazione = min(confidenza_autoregolazione, 0.6)
        if r["score_big5_coscienziosita"] is not None and \
                abs(r["score_big5_coscienziosita"] - r["eq_pilastro_autoregolazione"]) > 0.5:
            confidenza_autoregolazione = min(confidenza_autoregolazione, 0.6)
    if r["score_big5_gradevolezza"] is not None and r["eq_pilastro_empatia"] is not None:
        if abs((1 - r["score_big5_gradevolezza"]) - (1 - r["eq_pilastro_empatia"])) > 0.5:
            confidenza_empatia = min(confidenza_empatia, 0.6)

    cur.execute("""
        UPDATE psychometric_scores SET confidenza_eq_autoregolazione = %s, confidenza_eq_empatia = %s
        WHERE user_id = %s
    """, (confidenza_autoregolazione, confidenza_empatia, str(user_id)))

    quadrante_timoroso = (
        r["ansia_score"] is not None and r["evitamento_score"] is not None and
        r["ansia_score"] > 0.7 and r["evitamento_score"] > 0.7
    )

    # Insieme deduplicato per dimensione — 11 valori distinti, non un
    # contatore per-controllo (v. docstring sopra).
    insieme_confidenze = [
        r["confidenza_big5_estroversione"], r["confidenza_big5_gradevolezza"],
        r["confidenza_big5_coscienziosita"], r["confidenza_big5_nevroticismo"],
        r["confidenza_big5_apertura"],
        r["confidenza_eq_autoconsapevolezza"], confidenza_autoregolazione,
        confidenza_empatia, r["confidenza_eq_responsabilita"],
        r["confidenza_attaccamento_ansia"], r["confidenza_attaccamento_evitamento"],
    ]
    n_dimensioni_a_0_6 = sum(1 for v in insieme_confidenze if v == 0.6)

    flag = n_dimensioni_a_0_6 >= 2 or quadrante_timoroso or r["flag_trappola_fallita"] >= 1
    cur.execute("UPDATE psychometric_scores SET flag_profilo_per_revisione_dati = %s WHERE user_id = %s",
                (flag, str(user_id)))

    # Ricalcolo score_maturita_emotiva SOLO se i 4 pilastri EQ sono già stati
    # sottomessi — altrimenti (es. Big Five arrivato prima dell'EQ, ordine
    # normale del wizard) non c'è ancora nulla da correggere.
    pilastri = {
        "autoconsapevolezza": (r["eq_pilastro_autoconsapevolezza"], r["confidenza_eq_autoconsapevolezza"]),
        "autoregolazione": (r["eq_pilastro_autoregolazione"], confidenza_autoregolazione),
        "empatia": (r["eq_pilastro_empatia"], confidenza_empatia),
        "responsabilita": (r["eq_pilastro_responsabilita"], r["confidenza_eq_responsabilita"]),
    }
    if all(v is not None for v, _ in pilastri.values()):
        pesi_base = {
            "autoconsapevolezza": _config_float(cur, "weight_eq_autoconsapevolezza", 0.25),
            "autoregolazione": _config_float(cur, "weight_eq_autoregolazione", 0.25),
            "empatia": _config_float(cur, "weight_eq_empatia", 0.25),
            "responsabilita": _config_float(cur, "weight_eq_responsabilita", 0.25),
        }
        pesi_effettivi = {nome: pesi_base[nome] * conf for nome, (_, conf) in pilastri.items()}
        somma_pesi = sum(pesi_effettivi.values())
        maturita = sum(v * pesi_effettivi[nome] for nome, (v, _) in pilastri.items()) / somma_pesi

        cur.execute("UPDATE psychometric_scores SET score_maturita_emotiva = %s WHERE user_id = %s",
                    (maturita, str(user_id)))


@router.post("/bigfive", response_model=BigFiveResult)
def submit_big_five(user_id: UUID, payload: BigFiveSubmission):
    risultato, confidenza = calcola_big_five(payload.risposte)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE psychometric_scores SET
            score_big5_estroversione = %s, score_big5_gradevolezza = %s,
            score_big5_coscienziosita = %s, score_big5_nevroticismo = %s,
            score_big5_apertura = %s,
            confidenza_big5_estroversione = %s, confidenza_big5_gradevolezza = %s,
            confidenza_big5_coscienziosita = %s, confidenza_big5_nevroticismo = %s,
            confidenza_big5_apertura = %s
        WHERE user_id = %s
    """, (
        risultato.score_big5_estroversione, risultato.score_big5_gradevolezza,
        risultato.score_big5_coscienziosita, risultato.score_big5_nevroticismo,
        risultato.score_big5_apertura,
        confidenza["confidenza_big5_estroversione"], confidenza["confidenza_big5_gradevolezza"],
        confidenza["confidenza_big5_coscienziosita"], confidenza["confidenza_big5_nevroticismo"],
        confidenza["confidenza_big5_apertura"], str(user_id),
    ))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    _verifica_trappola(cur, user_id, payload.risposte, "T1")
    _ricalcola_confidenza_e_flag(cur, user_id)
    conn.commit()
    _tenta_report_personale(conn, cur, user_id)
    conn.close()
    return risultato


@router.post("/attaccamento", response_model=AttaccamentoResult)
def submit_attaccamento(user_id: UUID, payload: AttaccamentoSubmission):
    """Ainima_Test_Attaccamento_v1.md — 18 item, sostituisce la distribuzione
    a 4 stili prima dedotta dalla chat-intervista LLM."""
    risultato, confidenza = calcola_attaccamento(payload.risposte)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE psychometric_scores SET ansia_score = %s, evitamento_score = %s, stile_attaccamento = %s,
            confidenza_attaccamento_ansia = %s, confidenza_attaccamento_evitamento = %s
        WHERE user_id = %s
    """, (
        risultato.ansia_score, risultato.evitamento_score, risultato.stile_attaccamento,
        confidenza["confidenza_attaccamento_ansia"], confidenza["confidenza_attaccamento_evitamento"],
        str(user_id),
    ))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    _verifica_trappola(cur, user_id, payload.risposte, "T2")
    _ricalcola_confidenza_e_flag(cur, user_id)
    conn.commit()
    _tenta_report_personale(conn, cur, user_id)
    conn.close()
    return risultato


@router.post("/eq", response_model=EqResult)
def submit_eq(user_id: UUID, payload: EqSubmission):
    """Ainima_Test_EQScore_v1.md — 24 item, sostituisce il rubric-scorer LLM
    (Prompt 2) sulla chat-intervista."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM psychometric_scores WHERE user_id = %s", (str(user_id),))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    risultato, confidenza_interna = calcola_eq(payload.risposte, cur)
    cur.execute("""
        UPDATE psychometric_scores SET
            eq_pilastro_autoconsapevolezza = %s, eq_pilastro_autoregolazione = %s,
            eq_pilastro_empatia = %s, eq_pilastro_responsabilita = %s,
            score_maturita_emotiva = %s,
            confidenza_eq_autoconsapevolezza = %s, confidenza_eq_responsabilita = %s,
            confidenza_eq_autoregolazione_interna = %s, confidenza_eq_empatia_interna = %s,
            confidenza_eq_autoregolazione = %s, confidenza_eq_empatia = %s
        WHERE user_id = %s
    """, (
        risultato.eq_pilastro_autoconsapevolezza, risultato.eq_pilastro_autoregolazione,
        risultato.eq_pilastro_empatia, risultato.eq_pilastro_responsabilita,
        risultato.score_maturita_emotiva,
        confidenza_interna["autoconsapevolezza"], confidenza_interna["responsabilita"],
        confidenza_interna["autoregolazione"], confidenza_interna["empatia"],
        # valore pubblico iniziale = interna; _ricalcola_confidenza_e_flag()
        # sotto lo corregge subito con min(interna, incrociato §4b).
        confidenza_interna["autoregolazione"], confidenza_interna["empatia"],
        str(user_id),
    ))
    _verifica_trappola(cur, user_id, payload.risposte, "T3")
    _ricalcola_confidenza_e_flag(cur, user_id)
    # score_maturita_emotiva scritto sopra usa pesi ancora senza confidenza
    # (calcolata solo dentro _ricalcola_confidenza_e_flag, che legge il
    # confronto fresco con Big Five) — rilette qui perché la risposta API
    # rifletta il valore corretto, non quello provvisorio pre-rettifica.
    cur.execute("SELECT score_maturita_emotiva FROM psychometric_scores WHERE user_id = %s", (str(user_id),))
    risultato.score_maturita_emotiva = cur.fetchone()["score_maturita_emotiva"]
    conn.commit()
    _tenta_report_personale(conn, cur, user_id)
    conn.close()
    return risultato


@router.post("/profilo-relazionale", response_model=ProfiloRelazionaleResult)
def submit_profilo_relazionale(user_id: UUID, payload: ProfiloRelazionaleSubmission):
    """Ainima_Test_Profilo_Relazionale_v1.md — 26 item, sostituisce il
    confronto a embedding (self_embedding_vector/ideal_embedding_vector) nel
    calcolo di Coerenza Narrativa (RNF-11, Blocco D — v. CLAUDE.md)."""
    risultato = calcola_profilo_relazionale(payload.risposte)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE psychometric_scores SET
            profilo_valori_self = %s::jsonb, profilo_valori_partner_ideale = %s::jsonb,
            profilo_stile_vita_self = %s::jsonb, profilo_stile_vita_partner_ideale = %s::jsonb,
            profilo_dinamica_relazionale_self = %s::jsonb, profilo_dinamica_relazionale_partner_ideale = %s::jsonb,
            profilo_aspirazioni_self = %s::jsonb, profilo_aspirazioni_partner_ideale = %s::jsonb
        WHERE user_id = %s
    """, (
        json.dumps(risultato.profilo_valori_self), json.dumps(risultato.profilo_valori_partner_ideale),
        json.dumps(risultato.profilo_stile_vita_self), json.dumps(risultato.profilo_stile_vita_partner_ideale),
        json.dumps(risultato.profilo_dinamica_relazionale_self), json.dumps(risultato.profilo_dinamica_relazionale_partner_ideale),
        json.dumps(risultato.profilo_aspirazioni_self), json.dumps(risultato.profilo_aspirazioni_partner_ideale),
        str(user_id),
    ))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    conn.commit()
    _tenta_report_personale(conn, cur, user_id)
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

    # v. GENERAZIONE_PROFILO_CANONICO_ATTIVA in cima al file — in pausa
    # finché Prompt 5 non esiste per consumare questo output.
    if GENERAZIONE_PROFILO_CANONICO_ATTIVA and payload.descrizione_di_se:
        canonico = llm_pipeline.estrai_profilo_self(payload.descrizione_di_se)
        embedding = text_embedding.embed_testo(canonico)
        cur.execute("""
            UPDATE psychometric_scores SET self_profile_canonico = %s, self_embedding_vector = %s
            WHERE user_id = %s
        """, (canonico, embedding, str(user_id)))

    if GENERAZIONE_PROFILO_CANONICO_ATTIVA and payload.descrizione_partner_ideale:
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
