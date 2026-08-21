"""RF-08: criteri di ricerca dealbreaker/soft — tenuti in tabelle separate
per costruzione (v. Documento_Requisiti_v1.md §7.4, nota implementativa).
RF-08c: liste "Mi Piace/Non Sopporto" (Ainima_Liste_Piace_Detesta_v1.md) —
a differenza dei campi liberi narrativi, ENTRANO nel FINAL_SCORE
(Punteggio_Tag_Liste, STEP 4), quindi vivono in una tabella dedicata
(interest_tags), non in profile_narrative."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.interest_tags import InterestTagsUpdate
from schemas.preferences import DealbreakerCriteriaIn, SoftCriteriaIn
from services import tag_matching

router = APIRouter(prefix="/users/{user_id}", tags=["preferences"])


@router.get("/preferences")
def leggi_preferenze(user_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dealbreaker_criteria WHERE user_id = %s", (str(user_id),))
    dealbreaker = cur.fetchone()
    cur.execute("SELECT * FROM soft_criteria WHERE user_id = %s", (str(user_id),))
    soft = cur.fetchone()
    conn.close()
    if dealbreaker is None and soft is None:
        raise HTTPException(404, "Utente non trovato")
    return {"dealbreaker": dealbreaker, "soft": soft}


@router.put("/preferences/dealbreaker")
def aggiorna_dealbreaker(user_id: UUID, payload: DealbreakerCriteriaIn):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE dealbreaker_criteria SET
            pref_genere_cercato = %s, pref_eta_min = %s, pref_eta_max = %s,
            pref_accetta_figli = %s, pref_desidera_figli_futuri = %s
        WHERE user_id = %s
    """, (
        payload.pref_genere_cercato, payload.pref_eta_min, payload.pref_eta_max,
        payload.pref_accetta_figli, payload.pref_desidera_figli_futuri, str(user_id),
    ))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    conn.commit()
    conn.close()
    return {"aggiornato": True}


@router.get("/preferences/tags")
def leggi_liste_interessi(user_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT mi_piace, non_sopporto, partner_vorrei, partner_non_vorrei,
               mi_piace_tags, non_sopporto_tags, partner_vorrei_tags, partner_non_vorrei_tags
        FROM interest_tags WHERE user_id = %s
    """, (str(user_id),))
    riga = cur.fetchone()
    conn.close()
    if riga is None:
        raise HTTPException(404, "Utente non trovato")
    return riga


@router.put("/preferences/tags")
def aggiorna_liste_interessi(user_id: UUID, payload: InterestTagsUpdate):
    """RF-08c: parsing (split su virgola/trim/lowercase/dedup) + embedding
    per tag con cache condivisa (services/tag_matching.py) — solo i tag mai
    visti prima da NESSUN utente richiedono una chiamata di embedding."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id = %s", (str(user_id),))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    dati = payload.model_dump(exclude_unset=True)
    campi_testo = {k: v for k, v in dati.items() if v is not None}
    if not campi_testo:
        conn.close()
        return {"aggiornato": False, "nota": "nessun campo fornito"}

    campi_tags = {f"{k}_tags": tag_matching.normalizza_tag(v) for k, v in campi_testo.items()}

    tutti_i_tag = [t for lista in campi_tags.values() for t in lista]
    tag_matching.get_or_compute_embeddings(tutti_i_tag, cur)

    colonne = {**campi_testo, **campi_tags}
    # interest_tags non viene pre-creata alla registrazione (stessa
    # convenzione di profile_narrative, v. psychometric.py aggiorna_narrative)
    # — upsert, non un semplice UPDATE, altrimenti per un utente nuovo la
    # riga non esiste ancora e l'UPDATE sarebbe un no-op silenzioso (0 righe
    # toccate, nessun errore) mentre la risposta continuerebbe a dire
    # "aggiornato": true.
    set_clause = ", ".join(f"{k} = %s" for k in colonne)
    cur.execute(f"""
        INSERT INTO interest_tags (user_id, {', '.join(colonne)}, data_ultima_modifica)
        VALUES (%s, {', '.join(['%s'] * len(colonne))}, now())
        ON CONFLICT (user_id) DO UPDATE SET {set_clause}, data_ultima_modifica = now()
    """, (str(user_id), *colonne.values(), *colonne.values()))

    conn.commit()
    conn.close()
    return {"aggiornato": True, **campi_tags}


@router.put("/preferences/soft")
def aggiorna_soft(user_id: UUID, payload: SoftCriteriaIn):
    conn = get_conn()
    cur = conn.cursor()
    dati = payload.model_dump()
    set_clause = ", ".join(f"{k} = %s" for k in dati)
    cur.execute(f"UPDATE soft_criteria SET {set_clause} WHERE user_id = %s",
                (*dati.values(), str(user_id)))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    conn.commit()
    conn.close()
    return {"aggiornato": True}
