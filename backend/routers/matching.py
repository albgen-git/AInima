"""RF-10..RF-15: proposta mensile, accettazione/rifiuto. Il calcolo vero
e proprio vive in services/matching_engine.py."""

import json
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.matching import MatchDecision, ProposalOut
from services import couple_analysis, matching_engine
from services.email_provider import get_email_provider

router = APIRouter(tags=["matching"])

# Test Profilo Relazionale (Blocco D — v. CLAUDE.md): gli 8 campi JSON che
# punteggio_narrativo_strutturato() si aspetta nei dict a/b, stessi nomi di
# colonna della SELECT sotto — nessuna traduzione di chiave necessaria.
CAMPI_PROFILO_RELAZIONALE = [
    "profilo_valori_self", "profilo_valori_partner_ideale",
    "profilo_stile_vita_self", "profilo_stile_vita_partner_ideale",
    "profilo_dinamica_relazionale_self", "profilo_dinamica_relazionale_partner_ideale",
    "profilo_aspirazioni_self", "profilo_aspirazioni_partner_ideale",
]


@router.get("/users/{user_id}/affinity/{other_user_id}")
def analisi_affinita_narrativa(user_id: UUID, other_user_id: UUID):
    """Coerenza narrativa PRE-abbinamento tra due utenti specifici, su
    richiesta — aritmetica diretta sul Test Profilo Relazionale (Blocco D,
    v. CLAUDE.md — matching_engine.punteggio_narrativo_strutturato()), non
    più similarità a embedding né un Judge LLM (RNF-11: nessuna IA
    generativa nel calcolo dei punteggi). Richiede che entrambi abbiano
    completato il test (26 item, self + partner ideale).

    Endpoint admin/debug (mai chiamato dall'app utente — espone
    esplicitamente l'ID dell'altra persona, cosa che romperebbe
    l'anonimato RF-12 se mai finisse davanti a un utente finale): il flag
    di asimmetria è esposto grezzo, non riformulato — v. invece
    /proposal/analysis per la versione riformulata rivolta all'utente."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT user_id, {', '.join(CAMPI_PROFILO_RELAZIONALE)}
        FROM psychometric_scores WHERE user_id IN (%s, %s)
    """, (str(user_id), str(other_user_id)))
    # psycopg2 non ha mai register_uuid() attivo in questo progetto — una
    # colonna UUID diretta (non un'espressione calcolata) torna comunque
    # come str, mai come uuid.UUID: normalizza qui, non solo nei punti dove
    # una CASE WHEN la rende esplicitamente ambigua (bug preesistente
    # trovato testando dal vivo il Blocco D — mai una regressione introdotta
    # ora, l'endpoint dava sempre 404 anche prima).
    righe = {str(r["user_id"]): r for r in cur.fetchall()}
    conn.close()

    for uid in (str(user_id), str(other_user_id)):
        if uid not in righe:
            raise HTTPException(404, f"Utente {uid} non trovato")
        if any(righe[uid][c] is None for c in CAMPI_PROFILO_RELAZIONALE):
            raise HTTPException(
                409, f"Utente {uid} non ha ancora completato il Test Profilo Relazionale")

    punteggio, flag_asimmetria_narrativa, _ = matching_engine.punteggio_narrativo_strutturato(
        dict(righe[str(user_id)]), dict(righe[str(other_user_id)]))
    return {"punteggio_narrativo_strutturato": punteggio, "flag_asimmetria_narrativa": flag_asimmetria_narrativa}


@router.get("/users/{user_id}/proposal", response_model=ProposalOut | None)
def proposta_corrente(user_id: UUID):
    """RF-12: mostra la proposta del ciclo corrente in forma anonima —
    nessun nome/cognome/contatto finché non è Confermato (RF-20)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.match_id, m.stato, m.data_scadenza_risposta, m.user_a_id,
               CASE WHEN m.user_a_id = %s THEN m.user_b_id ELSE m.user_a_id END AS altro_id
        FROM matches m
        WHERE (m.user_a_id = %s OR m.user_b_id = %s)
          AND m.stato IN ('Proposto', 'Accettato_A', 'Accettato_B', 'Confermato')
          AND m.contatto_scambiato = FALSE
        ORDER BY m.data_proposta DESC LIMIT 1
    """, (str(user_id), str(user_id), str(user_id)))
    m = cur.fetchone()
    if not m:
        conn.close()
        return None

    # 'Accettato_A'/'Accettato_B' da soli sono ambigui lato client (non
    # sappiamo se l'utente corrente è il lato A o B, la proposta è
    # anonima) — calcolato qui, mai esposto direttamente come user_a_id.
    lato_mio = "A" if str(user_id) == str(m["user_a_id"]) else "B"
    lato_altro = "B" if lato_mio == "A" else "A"
    in_attesa_di_te = m["stato"] == "Proposto" or m["stato"] == f"Accettato_{lato_altro}"

    cur.execute("""
        SELECT EXTRACT(YEAR FROM age(u.data_nascita))::int AS eta, u.genere,
               p.corporatura, p.foto_profilo_url,
               s.coordinate_gps[0] AS lon, s.coordinate_gps[1] AS lat, so.titolo_studio
        FROM users u
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN socio_profile s ON s.user_id = u.user_id
        JOIN socio_profile so ON so.user_id = u.user_id
        WHERE u.user_id = %s
    """, (str(m["altro_id"]),))
    altro = cur.fetchone()

    cur.execute("SELECT coordinate_gps[0] AS lon, coordinate_gps[1] AS lat FROM socio_profile WHERE user_id = %s",
                (str(user_id),))
    mio = cur.fetchone()
    conn.close()

    distanza = None
    if mio and altro and mio["lon"] is not None and altro["lon"] is not None:
        distanza = matching_engine.haversine_km(mio["lon"], mio["lat"], altro["lon"], altro["lat"])

    return ProposalOut(
        match_id=m["match_id"], stato=m["stato"], eta=altro["eta"], genere=altro["genere"],
        corporatura=altro["corporatura"], titolo_studio=altro["titolo_studio"],
        foto_profilo_url=altro["foto_profilo_url"], distanza_km=distanza,
        data_scadenza_risposta=m["data_scadenza_risposta"],
        in_attesa_di_te=in_attesa_di_te,
    )



# Rivolto all'utente finale (proposal/page.tsx) — mai un booleano grezzo né
# una frase diretta ("il partner ha detto di detestare X"), stesso
# principio già seguito per il report EQ: un possibile spunto di confronto,
# mai un'etichetta. Un'unica frase condivisa per entrambi i flag (asimmetria
# narrativa + rifiuto esplicito nelle liste) — separarle rischierebbe di
# sembrare un elenco di allarmi invece di un invito generico al dialogo.
SPUNTO_ATTENZIONE_COSTRUTTIVO = (
    "Su alcuni valori, stile di vita o abitudini potreste avere punti di vista "
    "piuttosto diversi — potrebbe valere la pena parlarne apertamente appena vi conoscerete."
)


def _calcola_analisi(conn, cur, match_id: str, user_id: str, altro_id: str, flag_rifiuto: bool, flag_asimmetria: bool):
    """Nucleo condiviso tra /proposal/analysis (proposta attiva corrente)
    e /matches/{match_id}/analysis (qualunque match, incluso Rubrica) —
    stessa aritmetica sul Test Profilo Relazionale, stessa riformulazione
    del risultato in un unico spunto costruttivo generico (mai quale dei
    due flag, mai un dettaglio specifico — l'anonimato/la delicatezza del
    dato restano garantiti in entrambi i punti di chiamata).

    RF-12: include anche la sintesi caratteriale di coppia (services/
    couple_analysis.py — genera solo se non già presente per questo
    match_id, mai rigenerata ad ogni chiamata). Un fallimento di
    generazione (LLM lento/non disponibile) non deve mai far fallire
    l'intero endpoint — degrado a sintesi_caratteriale_coppia: None,
    stesso principio già applicato al report personale RF-28.

    2026-09-02 (v. CLAUDE.md, bug reale trovato testando la Rubrica dal
    vivo): il gate precedente richiedeva che ENTRAMBI gli utenti avessero
    completato tutte le 8 colonne del Test Profilo Relazionale prima di
    ritornare qualunque cosa — bloccando anche sintesi_caratteriale_coppia,
    che invece services/couple_analysis.py sa già generare con quel dato
    mancante (fallback neutro, verificato con generazioni reali). Il caso
    Alberto/Patrizia (Patrizia non ha completato il test) aveva un testo
    già generato e salvato nel DB che la Rubrica non mostrava mai per
    questo motivo. Ora il gate richiede solo che esista una riga
    psychometric_scores per entrambi (creata alla registrazione, v.
    schema — quindi praticamente sempre vera) — punteggio_narrativo_
    strutturato() gestisce da sola il dato mancante restituendo il suo
    fallback neutro (0.5, v. matching_engine.py), esattamente come già
    faceva prima di questo fix per gli usi interni al motore di scoring."""
    cur.execute(f"""
        SELECT user_id, {', '.join(CAMPI_PROFILO_RELAZIONALE)}
        FROM psychometric_scores WHERE user_id IN (%s, %s)
    """, (user_id, altro_id))
    # CASE WHEN ... (o un valore letto da una tabella con FK) può tornare
    # come stringa (non UUID) da psycopg2 — normalizza entrambi i lati a
    # str prima di confrontare (v. bug trovato in test manuale: confronto
    # UUID/str falliva silenziosamente).
    righe = {str(r["user_id"]): r for r in cur.fetchall()}

    if user_id not in righe or altro_id not in righe:
        return {"pronta": False, "analisi": None}

    punteggio, _, _ = matching_engine.punteggio_narrativo_strutturato(dict(righe[user_id]), dict(righe[altro_id]))
    spunto = SPUNTO_ATTENZIONE_COSTRUTTIVO if (flag_rifiuto or flag_asimmetria) else None

    sintesi = None
    try:
        sintesi = couple_analysis.genera_e_salva(conn, cur, match_id, user_id, altro_id)
    except Exception as e:
        print(f"[ERRORE] generazione sintesi caratteriale coppia per match {match_id} fallita: {e}")

    return {"pronta": True, "analisi": {
        "punteggio_narrativo_strutturato": punteggio,
        "spunto_di_attenzione": spunto,
        "sintesi_caratteriale_coppia": sintesi,
    }}


@router.get("/users/{user_id}/proposal/analysis")
def analisi_proposta_corrente(user_id: UUID):
    """Coerenza narrativa della proposta del ciclo corrente — aritmetica
    diretta sul Test Profilo Relazionale (v. nota su /affinity sopra),
    pensata per la schermata "Proposta di match".

    A differenza di GET /users/{id}/affinity/{other_id}, questo endpoint
    NON richiede né espone mai l'ID dell'altra persona: lo risolve
    internamente dalla proposta attiva dell'utente (stessa query di
    GET /users/{id}/proposal) e restituisce solo il punteggio —
    l'anonimato della proposta (RF-12) resta intatto anche qui.

    Include anche 'Confermato' (bug reale trovato dal vivo, v. CLAUDE.md):
    prima si fermava a 'Proposto'/'Accettato_*', quindi un utente che
    restava sulla schermata Proposta dopo aver pagato vedeva la card
    dell'analisi bloccata su "caricamento" per sempre (la chiamata 404ava
    e il frontend la ignorava silenziosamente) — stesso motivo per cui
    GET /users/{id}/proposal era già stato esteso in una sessione
    precedente."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.match_id, CASE WHEN m.user_a_id = %s THEN m.user_b_id ELSE m.user_a_id END AS altro_id,
               m.flag_rifiuto_esplicito, m.flag_asimmetria_narrativa
        FROM matches m
        WHERE (m.user_a_id = %s OR m.user_b_id = %s)
          AND m.stato IN ('Proposto', 'Accettato_A', 'Accettato_B', 'Confermato')
        ORDER BY m.data_proposta DESC LIMIT 1
    """, (str(user_id), str(user_id), str(user_id)))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Nessuna proposta attiva per questo utente")

    risultato = _calcola_analisi(conn, cur, str(m["match_id"]), str(user_id), str(m["altro_id"]),
                                  m["flag_rifiuto_esplicito"], m["flag_asimmetria_narrativa"])
    conn.close()
    return risultato


@router.get("/users/{user_id}/matches/{match_id}/analysis")
def analisi_match(user_id: UUID, match_id: UUID):
    """Come /proposal/analysis ma per UN match specifico invece che "la
    proposta attiva corrente" — usato dalla Rubrica (RF-22b), dove più
    abbinamenti conclusi possono coesistere nel tempo. Nessun vincolo di
    stato: funziona per qualunque match, non solo quelli ancora aperti,
    dato che qui il chiamante fornisce già il match_id (l'anonimato RF-12
    non è in gioco — l'utente ha già il contatto reale se è arrivato in
    Rubrica)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT CASE WHEN user_a_id = %s THEN user_b_id ELSE user_a_id END AS altro_id,
               user_a_id, user_b_id, flag_rifiuto_esplicito, flag_asimmetria_narrativa
        FROM matches WHERE match_id = %s
    """, (str(user_id), str(match_id)))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non trovato")
    if str(user_id) not in (str(m["user_a_id"]), str(m["user_b_id"])):
        conn.close()
        raise HTTPException(403, "Questo match non appartiene all'utente indicato")

    risultato = _calcola_analisi(conn, cur, str(match_id), str(user_id), str(m["altro_id"]),
                                  m["flag_rifiuto_esplicito"], m["flag_asimmetria_narrativa"])
    conn.close()
    return risultato


@router.post("/users/{user_id}/matches/{match_id}/decision")
def decidi_match(user_id: UUID, match_id: UUID, payload: MatchDecision):
    """RF-13/14/15: entrambe le parti devono accettare entro la finestra
    (RF-14) perché il match diventi 'ufficiale'; un rifiuto lo fa decadere
    subito (RF-15, nessun ripescaggio immediato)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_a_id, user_b_id, stato FROM matches WHERE match_id = %s", (str(match_id),))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non trovato")
    if str(user_id) not in (str(m["user_a_id"]), str(m["user_b_id"])):
        conn.close()
        raise HTTPException(403, "Questo match non appartiene all'utente indicato")
    if m["stato"] not in ("Proposto", "Accettato_A", "Accettato_B"):
        conn.close()
        raise HTTPException(409, f"Match già in stato finale: {m['stato']}")

    lato = "A" if str(user_id) == str(m["user_a_id"]) else "B"

    if not payload.accetta:
        cur.execute("UPDATE matches SET stato = 'Rifiutato' WHERE match_id = %s", (str(match_id),))
        conn.commit()
        conn.close()
        return {"stato": "Rifiutato"}

    nuovo_stato = None
    if m["stato"] == "Proposto":
        nuovo_stato = f"Accettato_{lato}"
    elif m["stato"] == f"Accettato_{'B' if lato == 'A' else 'A'}":
        # l'altra parte aveva già accettato -> entrambe hanno accettato
        nuovo_stato = "Confermato"
    else:
        conn.close()
        raise HTTPException(409, "Hai già accettato questo match")

    cur.execute("UPDATE matches SET stato = %s WHERE match_id = %s", (nuovo_stato, str(match_id)))
    conn.commit()
    conn.close()
    esito = {"stato": nuovo_stato}
    if nuovo_stato == "Confermato":
        esito["nota"] = "Entrambe le parti hanno accettato — procedere con il pagamento (RF-17)"
    return esito


@router.post("/admin/matching/run-cycle")
def esegui_ciclo_mensile(dry_run: bool = True):
    """RF-10/11: genera le proposte del mese per tutti gli utenti Attivi,
    tramite abbinamento stabile (v. services/matching_engine.stable_match —
    calcola le preferenze di tutti prima di decidere qualunque coppia,
    risolve il problema di reciprocità del ciclo greedy iniziale). dry_run
    =True (default) calcola senza scrivere — passare dry_run=false per
    generare davvero le righe in 'matches' (da schedulare come cron
    mensile in produzione, v. RF-11).

    RF-12, nota deliberata: a differenza di /admin/matching/propose/{id}
    (un solo match, genera la sintesi caratteriale di coppia in modo
    sincrono), QUESTO endpoint NON genera la sintesi per le potenzialmente
    centinaia di coppie create in un run reale — farlo qui, sincrono,
    dentro una singola richiesta HTTP, rischierebbe lo stesso timeout/OOM
    già trovato e risolto per il caricamento del pool (v. CLAUDE.md). La
    sintesi per i match creati da qui viene generata pigramente alla prima
    GET /users/{id}/proposal/analysis o /matches/{id}/analysis (v.
    _calcola_analisi sotto) — nessuno scheduler/coda reale per pre-
    generarle in background, stesso limite già accettato altrove nel
    progetto per i cicli periodici."""
    conn = get_conn()
    risultati = matching_engine.run_monthly_batch(conn, dry_run=dry_run)
    conn.close()

    riepilogo = {}
    utenti_coperti = 0
    for r in risultati:
        riepilogo[r["esito"]] = riepilogo.get(r["esito"], 0) + 1
        utenti_coperti += 2 if r["esito"] == "proposta" else 1
    return {"dry_run": dry_run, "utenti_coperti": utenti_coperti, "coppie_e_singoli": len(risultati), "riepilogo": riepilogo}


@router.post("/admin/matching/propose/{user_id}")
def proponi_match_singolo(user_id: UUID):
    """Trigger mirato per UN singolo utente — a differenza di run-cycle
    (che ricalcola l'intero pool con l'abbinamento stabile), usa
    find_best_match() così com'è già per l'anteprima/affinity, utile per
    test/dimostrazioni senza rigenerare le proposte di migliaia di altri
    profili demo. Stesse colonne scritte in 'matches' di run_monthly_batch.

    Gap reale trovato mentre veniva richiesto questo trigger: nessun
    codice invia un'email alla creazione di una proposta, né qui né nel
    batch mensile — RF-11/12/13 non lo richiedono esplicitamente (a
    differenza di RF-29 per il report personale), ma l'utente la vuole per
    questo test — v. CLAUDE.md. Notifica inviata a entrambe le parti, mai
    il contenuto/identità del match (RF-12, proposta anonima) — solo
    l'invito a controllare la propria area personale."""
    conn = get_conn()
    cur = conn.cursor()
    pool = matching_engine.load_pool(cur)
    if str(user_id) not in pool:
        conn.close()
        raise HTTPException(404, "Utente non trovato nel pool di matching (deve essere Attivo)")

    cfg = matching_engine.load_config_floats(cur)
    esito = matching_engine.find_best_match(str(user_id), pool, cfg)
    if esito["esito"] != "proposta":
        conn.close()
        return {"esito": esito["esito"]}

    cand_id = esito["candidato_id"]
    scadenza = datetime.now(timezone.utc) + timedelta(days=int(cfg.get("finestra_risposta_match_giorni", 7)))
    cur.execute("""
        INSERT INTO matches (user_a_id, user_b_id, stato, final_score,
                             data_scadenza_risposta, algoritmo_versione, algoritmo_parametri,
                             shortlist_candidati, selezionato_per_somiglianza_visiva,
                             flag_rifiuto_esplicito, flag_asimmetria_narrativa)
        VALUES (%s, %s, 'Proposto', %s, %s, %s, %s::jsonb, %s::uuid[], %s, %s, %s)
        RETURNING match_id
    """, (str(user_id), str(cand_id), esito["final_score"], scadenza,
          matching_engine.ALGORITMO_VERSIONE, json.dumps(cfg),
          [str(c) for c in esito["shortlist"]], bool(esito["selezionato_per_somiglianza_visiva"]),
          bool(esito["flag_rifiuto_esplicito"]), bool(esito["flag_asimmetria_narrativa"])))
    match_id = cur.fetchone()["match_id"]
    conn.commit()

    # RF-12: genera la sintesi caratteriale di coppia una volta qui, alla
    # creazione del match (non aspetta la prima GET) — un fallimento non
    # deve mai bloccare la creazione della proposta né l'invio email sotto.
    try:
        couple_analysis.genera_e_salva(conn, cur, str(match_id), str(user_id), str(cand_id))
    except Exception as e:
        print(f"[ERRORE] generazione sintesi caratteriale coppia per match {match_id} fallita: {e}")

    frontend_url = os.environ.get("FRONTEND_BASE_URL", "https://ainima.netlify.app")
    for uid in (str(user_id), str(cand_id)):
        try:
            cur.execute("SELECT email FROM users WHERE user_id = %s", (uid,))
            email = cur.fetchone()["email"]
            get_email_provider().invia_notifica(
                email, "Hai una nuova proposta di abbinamento",
                "<p>Ainima ti ha proposto un nuovo abbinamento questo mese.</p>"
                "<p>Vai alla tua area personale per scoprire chi è.</p>"
                f"<p><a href=\"{frontend_url}/it/proposal\">Vedi la proposta</a></p>",
            )
        except Exception as e:
            print(f"[ERRORE] invio email nuova proposta a {uid} fallito: {e}")

    conn.close()
    return {
        "esito": "proposta", "match_id": match_id, "candidato_id": cand_id,
        "final_score": esito["final_score"],
    }
