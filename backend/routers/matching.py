"""RF-10..RF-15: proposta mensile, accettazione/rifiuto. Il calcolo vero
e proprio vive in services/matching_engine.py."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.matching import MatchDecision, ProposalOut
from services import matching_engine

router = APIRouter(tags=["matching"])


@router.get("/users/{user_id}/affinity/{other_user_id}")
def analisi_affinita_narrativa(user_id: UUID, other_user_id: UUID):
    """Coerenza narrativa PRE-abbinamento tra due utenti specifici, su
    richiesta — calcolo vettoriale puro (cosine similarity tra self/ideal
    embedding, v. matching_engine.coerenza_narrativa_score), non più un
    Judge LLM (Prompt 4, rimosso — v. CLAUDE.md 2026-08-19, RNF-11: nessuna
    IA generativa nel calcolo dei punteggi di compatibilità). Richiede che
    entrambi abbiano compilato i due campi liberi RF-07b (self/ideal
    embedding già calcolati)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, self_embedding_vector, ideal_embedding_vector
        FROM psychometric_scores WHERE user_id IN (%s, %s)
    """, (str(user_id), str(other_user_id)))
    righe = {r["user_id"]: r for r in cur.fetchall()}
    conn.close()

    for uid in (user_id, other_user_id):
        if uid not in righe:
            raise HTTPException(404, f"Utente {uid} non trovato")
        if righe[uid]["self_embedding_vector"] is None or righe[uid]["ideal_embedding_vector"] is None:
            raise HTTPException(
                409, f"Utente {uid} non ha ancora compilato i campi liberi RF-07b "
                     "(servono self_embedding_vector e ideal_embedding_vector)")

    a, b = righe[user_id], righe[other_user_id]
    punteggio = matching_engine.coerenza_narrativa_score(
        {"self_emb": a["self_embedding_vector"], "ideal_emb": a["ideal_embedding_vector"]},
        {"self_emb": b["self_embedding_vector"], "ideal_emb": b["ideal_embedding_vector"]},
    )
    return {"compatibilita_narrativa_complessiva": punteggio}


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


@router.get("/users/{user_id}/proposal/analysis")
def analisi_proposta_corrente(user_id: UUID):
    """Coerenza narrativa della proposta del ciclo corrente — calcolo
    vettoriale puro (v. nota su /affinity sopra), pensata per la schermata
    "Proposta di match".

    A differenza di GET /users/{id}/affinity/{other_id}, questo endpoint
    NON richiede né espone mai l'ID dell'altra persona: lo risolve
    internamente dalla proposta attiva dell'utente (stessa query di
    GET /users/{id}/proposal) e restituisce solo il punteggio —
    l'anonimato della proposta (RF-12) resta intatto anche qui."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT CASE WHEN m.user_a_id = %s THEN m.user_b_id ELSE m.user_a_id END AS altro_id
        FROM matches m
        WHERE (m.user_a_id = %s OR m.user_b_id = %s) AND m.stato IN ('Proposto', 'Accettato_A', 'Accettato_B')
        ORDER BY m.data_proposta DESC LIMIT 1
    """, (str(user_id), str(user_id), str(user_id)))
    m = cur.fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Nessuna proposta attiva per questo utente")

    altro_id = str(m["altro_id"])
    cur.execute("""
        SELECT user_id, self_embedding_vector, ideal_embedding_vector
        FROM psychometric_scores WHERE user_id IN (%s, %s)
    """, (str(user_id), altro_id))
    # CASE WHEN ... restituisce il tipo come stringa (non UUID) da psycopg2 —
    # normalizza entrambi i lati a str prima di confrontare (v. bug trovato
    # in test manuale: confronto UUID/str falliva silenziosamente).
    righe = {str(r["user_id"]): r for r in cur.fetchall()}
    conn.close()

    for uid in (str(user_id), altro_id):
        if uid not in righe or righe[uid]["self_embedding_vector"] is None or righe[uid]["ideal_embedding_vector"] is None:
            return {"pronta": False, "analisi": None}

    io, altro = righe[str(user_id)], righe[altro_id]
    punteggio = matching_engine.coerenza_narrativa_score(
        {"self_emb": io["self_embedding_vector"], "ideal_emb": io["ideal_embedding_vector"]},
        {"self_emb": altro["self_embedding_vector"], "ideal_emb": altro["ideal_embedding_vector"]},
    )
    return {"pronta": True, "analisi": {"compatibilita_narrativa_complessiva": punteggio}}


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
    mensile in produzione, v. RF-11)."""
    conn = get_conn()
    risultati = matching_engine.run_monthly_batch(conn, dry_run=dry_run)
    conn.close()

    riepilogo = {}
    utenti_coperti = 0
    for r in risultati:
        riepilogo[r["esito"]] = riepilogo.get(r["esito"], 0) + 1
        utenti_coperti += 2 if r["esito"] == "proposta" else 1
    return {"dry_run": dry_run, "utenti_coperti": utenti_coperti, "coppie_e_singoli": len(risultati), "riepilogo": riepilogo}
