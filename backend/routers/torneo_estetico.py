"""Torneo estetico — spareggio secondario tramite preferenza estetica
(v. CLAUDE.md 2026-09-06). Non tocca pesi/soglie del FINAL_SCORE
esistente: alimenta solo preferenza_estetica_utente, consultata da
services/matching_engine.py SOLO quando due o più candidati sono già
quasi pari per punteggio caratteriale (system_config.soglia_pareggio_
final_score)."""

import random
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from db import get_conn
from schemas.torneo_estetico import (
    ConfrontoIn,
    ConfrontoOut,
    Partecipante,
    PreferenzaEsteticaOut,
    TorneoInizio,
)
from services import face_recognition

router = APIRouter(prefix="/users/{user_id}/torneo-estetico", tags=["torneo-estetico"])

POSIZIONI = ["A", "B", "C", "D", "E", "F", "G", "H"]


@router.get("/preferenza", response_model=PreferenzaEsteticaOut)
def leggi_preferenza(user_id: UUID):
    """Stato attuale, se il torneo è già stato completato almeno una
    volta — il frontend lo usa per mostrare l'esito invece di forzare
    l'utente a rifare il torneo per scoprirlo."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT data_completamento, foto_preferenza_urls FROM preferenza_estetica_utente WHERE user_id = %s",
        (str(user_id),),
    )
    riga = cur.fetchone()
    conn.close()
    if not riga:
        return PreferenzaEsteticaOut(completato=False)
    return PreferenzaEsteticaOut(
        completato=True,
        data_completamento=riga["data_completamento"],
        foto_preferenza_urls=riga["foto_preferenza_urls"],
    )


@router.post("/inizia", response_model=TorneoInizio)
def inizia_torneo(user_id: UUID):
    """Genere target = dealbreaker_criteria.pref_genere_cercato dell'utente
    — il torneo confronta solo foto del genere che l'utente cerca (v.
    CLAUDE.md, decisione esplicita). Posizioni A-H assegnate con un
    ordine casuale ad ogni sessione, per evitare bias di posizione
    sistematico (stesso principio già applicato altrove nel progetto,
    es. randomizzazione domande trappola)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pref_genere_cercato FROM dealbreaker_criteria WHERE user_id = %s", (str(user_id),))
    riga = cur.fetchone()
    if not riga:
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    genere_cercato = riga["pref_genere_cercato"]
    if genere_cercato not in ("Maschile", "Femminile"):
        conn.close()
        raise HTTPException(
            422,
            "Il torneo estetico richiede un genere cercato specifico (Maschile o Femminile) "
            "nei tuoi criteri di ricerca — imposta prima quella preferenza.",
        )

    cur.execute(
        "SELECT cluster_id, foto_url FROM torneo_estetico_cluster WHERE genere = %s ORDER BY cluster_id",
        (genere_cercato,),
    )
    cluster = cur.fetchall()
    conn.close()
    if len(cluster) != 8:
        raise HTTPException(
            409,
            f"Il pool di rappresentanti per '{genere_cercato}' non è pronto (trovati {len(cluster)}, attesi 8) "
            "— rilancia scripts/genera_cluster_torneo_estetico.py.",
        )

    random.shuffle(cluster)
    partecipanti = [
        Partecipante(posizione=POSIZIONI[i], cluster_id=c["cluster_id"], foto_url=c["foto_url"])
        for i, c in enumerate(cluster)
    ]
    return TorneoInizio(sessione_id=uuid4(), partecipanti=partecipanti)


def _espandi_preferenza(cur, conn, user_id: UUID, cluster_vincitore_id: UUID):
    """Parte 3: dal cluster vincitore, seleziona via CompareFaces le 10
    foto del POOL INTERO (non solo del cluster) più simili alla foto
    rappresentante — nessun ulteriore input richiesto all'utente. Chiamate
    AWS dal vivo, una tantum per utente al completamento del torneo (non
    ripetuta ad ogni match), non per l'intero pool demo."""
    cur.execute("SELECT genere, foto_url FROM torneo_estetico_cluster WHERE cluster_id = %s", (str(cluster_vincitore_id),))
    vincitore = cur.fetchone()
    if not vincitore:
        raise HTTPException(404, "Cluster vincitore non trovato")

    cur.execute("""
        SELECT p.foto_profilo_url
        FROM users u JOIN physical_profile p ON p.user_id = u.user_id
        WHERE u.is_demo = TRUE AND u.genere = %s AND p.foto_profilo_url IS NOT NULL
          AND p.foto_profilo_url != %s
    """, (vincitore["genere"], vincitore["foto_url"]))
    pool = cur.fetchall()

    punteggi = []
    for r in pool:
        sim = face_recognition.confronta_foto(vincitore["foto_url"], r["foto_profilo_url"])
        if sim is not None:
            punteggi.append((sim, r["foto_profilo_url"]))

    punteggi.sort(key=lambda x: x[0], reverse=True)
    top10 = [url for _, url in punteggi[:10]]

    cur.execute("""
        INSERT INTO preferenza_estetica_utente (user_id, cluster_id_vincitore, foto_preferenza_urls)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            cluster_id_vincitore = EXCLUDED.cluster_id_vincitore,
            foto_preferenza_urls = EXCLUDED.foto_preferenza_urls,
            data_completamento = now()
    """, (str(user_id), str(cluster_vincitore_id), top10))
    conn.commit()
    return top10


@router.post("/confronto", response_model=ConfrontoOut)
def registra_confronto(user_id: UUID, payload: ConfrontoIn):
    if payload.cluster_id_vincitore not in (payload.cluster_id_a, payload.cluster_id_b):
        raise HTTPException(422, "cluster_id_vincitore deve essere uno dei due partecipanti del confronto")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO torneo_estetico_confronti
            (user_id, sessione_id, turno, cluster_id_a, cluster_id_b, cluster_id_vincitore)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        str(user_id), str(payload.sessione_id), payload.turno,
        str(payload.cluster_id_a), str(payload.cluster_id_b), str(payload.cluster_id_vincitore),
    ))
    conn.commit()

    if payload.turno < 3:
        conn.close()
        return ConfrontoOut(completato=False)

    top10 = _espandi_preferenza(cur, conn, user_id, payload.cluster_id_vincitore)
    conn.close()
    return ConfrontoOut(
        completato=True,
        cluster_id_vincitore_torneo=payload.cluster_id_vincitore,
        foto_preferenza_urls=top10,
    )
