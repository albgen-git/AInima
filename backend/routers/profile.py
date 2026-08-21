"""RF-06, RF-08b, RF-06b: profilo anagrafico/fisico/socio-economico + foto
+ moderazione automatica dei contenuti fotografici. V. Documento_Requisiti_v1.md
§7.2-7.3, §7.9."""

import os
import shutil
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from db import get_conn
from schemas.users import ProfileUpdate
from services.content_moderation import get_content_moderation_provider

router = APIRouter(prefix="/users/{user_id}", tags=["profile"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "photos")


def _user_exists(cur, user_id):
    cur.execute("SELECT 1 FROM users WHERE user_id = %s", (str(user_id),))
    return cur.fetchone() is not None


@router.get("/profile")
def leggi_profilo(user_id: UUID):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.nome, u.cognome, u.data_nascita, u.genere, u.orientamento_sessuale,
               u.telefono, u.email, u.email_verificata,
               u.stato_civile, u.ha_figli,
               p.altezza_cm, p.peso_kg, p.corporatura, p.colore_capelli, p.colore_occhi,
               p.fumo, p.alcol, p.stile_vita_sport, p.foto_profilo_url, p.foto_partner_ideale_url,
               s.comune_residenza, s.titolo_studio, s.settore_occupazionale,
               s.fascia_reddito, s.fede_religiosa, s.importanza_religione,
               s.importanza_vicinanza_geografica, s.lingue_parlate
        FROM users u
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN socio_profile s ON s.user_id = u.user_id
        WHERE u.user_id = %s
    """, (str(user_id),))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Utente non trovato")
    return row


@router.put("/profile")
def aggiorna_profilo(user_id: UUID, payload: ProfileUpdate):
    conn = get_conn()
    cur = conn.cursor()
    if not _user_exists(cur, user_id):
        conn.close()
        raise HTTPException(404, "Utente non trovato")

    dati = payload.model_dump(exclude_unset=True)

    campi_users = {
        k: dati[k]
        for k in ("nome", "cognome", "data_nascita", "genere", "telefono",
                   "orientamento_sessuale", "stato_civile", "ha_figli")
        if k in dati
    }
    if campi_users:
        set_clause = ", ".join(f"{k} = %s" for k in campi_users)
        cur.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s",
                    (*campi_users.values(), str(user_id)))

    if dati.get("consenso_dati_sensibili") is True:
        # timestamp scritto solo quando il consenso viene dato davvero (mai
        # in caso di 'false' — bloccato a monte dal validator dello schema)
        cur.execute("""
            UPDATE users SET consenso_dati_sensibili = TRUE, consenso_dati_sensibili_at = now()
            WHERE user_id = %s
        """, (str(user_id),))

    campi_fisici = {k: dati[k] for k in ("altezza_cm", "peso_kg", "corporatura", "colore_capelli",
                                          "colore_occhi", "fumo", "alcol", "stile_vita_sport") if k in dati}
    if "altezza_cm" in campi_fisici:
        # anti-cheat (v. CLAUDE.md, richiesta esplicita dell'utente): l'altezza
        # non cambia nel tempo, a differenza degli altri campi fisici — una
        # volta impostata la prima volta (valore reale non NULL), non è più
        # modificabile via questo endpoint. Scartata in silenzio, non un
        # errore: gli altri campi nello stesso payload restano comunque salvati.
        cur.execute("SELECT altezza_cm FROM physical_profile WHERE user_id = %s", (str(user_id),))
        if cur.fetchone()["altezza_cm"] is not None:
            del campi_fisici["altezza_cm"]
    if campi_fisici:
        set_clause = ", ".join(f"{k} = %s" for k in campi_fisici)
        cur.execute(f"UPDATE physical_profile SET {set_clause} WHERE user_id = %s",
                    (*campi_fisici.values(), str(user_id)))

    campi_socio = {k: dati[k] for k in ("comune_residenza", "titolo_studio", "settore_occupazionale",
                                         "fascia_reddito", "fede_religiosa", "importanza_religione",
                                         "lingue_parlate") if k in dati}
    if campi_socio:
        set_clause = ", ".join(f"{k} = %s" for k in campi_socio)
        cur.execute(f"UPDATE socio_profile SET {set_clause} WHERE user_id = %s",
                    (*campi_socio.values(), str(user_id)))

    if payload.lat is not None and payload.lon is not None:
        cur.execute("UPDATE socio_profile SET coordinate_gps = point(%s, %s) WHERE user_id = %s",
                    (payload.lon, payload.lat, str(user_id)))

    if payload.importanza_vicinanza_geografica is not None:
        # stessa normalizzazione 1-5 -> 0.0-1.0 usata per i punteggi Big Five
        # (v. routers/psychometric.py calcola_big_five).
        normalizzata = (payload.importanza_vicinanza_geografica - 1) / 4
        cur.execute("UPDATE socio_profile SET importanza_vicinanza_geografica = %s WHERE user_id = %s",
                    (normalizzata, str(user_id)))

    conn.commit()
    conn.close()
    return {"aggiornato": True}


def _salva_foto(user_id: UUID, sottocartella: str, file: UploadFile) -> str:
    os.makedirs(os.path.join(STORAGE_DIR, sottocartella), exist_ok=True)
    estensione = os.path.splitext(file.filename or "")[1] or ".jpg"
    nome_file = f"{user_id}{estensione}"
    percorso_assoluto = os.path.join(STORAGE_DIR, sottocartella, nome_file)
    with open(percorso_assoluto, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"{sottocartella}/{nome_file}"


def _modera_foto(cur, user_id: UUID, tipo_immagine: str, percorso_relativo: str, percorso_assoluto: str) -> str:
    """RF-06b: scansiona la foto appena caricata, registra l'esito in
    content_moderation_log e — solo se effettivamente 'Sospetta' (non se il
    provider è assente/fallisce, v. services/content_moderation.py) —
    porta l'account in 'In attesa - verifica moderazione' (RF-09), bloccato
    finché uno staff non approva dalla coda (RF-25c). Ritorna l'esito."""
    risultato = get_content_moderation_provider().analizza(percorso_assoluto)
    cur.execute("""
        INSERT INTO content_moderation_log (user_id, tipo_immagine, immagine_url, esito_automatico, score_confidenza)
        VALUES (%s, %s, %s, %s, %s)
    """, (str(user_id), tipo_immagine, percorso_relativo, risultato.esito, risultato.score_confidenza))
    if risultato.esito == "Sospetta":
        cur.execute("""
            UPDATE users SET stato_account = 'In attesa - verifica moderazione'
            WHERE user_id = %s AND stato_account != 'Attivo'
        """, (str(user_id),))
    return risultato.esito


@router.post("/profile-photo")
def carica_foto_profilo(user_id: UUID, file: UploadFile = File(...)):
    """Salva il file + moderazione automatica (RF-06b). NON calcola
    l'embedding visivo (richiede un modello di face-embedding tipo ArcFace,
    non installato in questo ambiente — v. CLAUDE.md sulle limitazioni di
    pgvector/DeepFace). embedding_visivo_profilo resta NULL finché non gira
    una pipeline offline dedicata."""
    conn = get_conn()
    cur = conn.cursor()
    if not _user_exists(cur, user_id):
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    percorso = _salva_foto(user_id, "profilo", file)
    cur.execute("UPDATE physical_profile SET foto_profilo_url = %s WHERE user_id = %s",
                (percorso, str(user_id)))
    esito_moderazione = _modera_foto(cur, user_id, "Foto profilo", percorso,
                                      os.path.join(STORAGE_DIR, percorso))
    conn.commit()
    conn.close()
    return {"foto_profilo_url": percorso, "embedding_calcolato": False, "esito_moderazione": esito_moderazione}


@router.post("/ideal-partner-photo")
def carica_foto_partner_ideale(user_id: UUID, file: UploadFile = File(...)):
    """RF-08b: foto opzionale di riferimento estetico + moderazione
    automatica (RF-06b). Come per il profilo, l'embedding non è calcolato
    qui (stub)."""
    conn = get_conn()
    cur = conn.cursor()
    if not _user_exists(cur, user_id):
        conn.close()
        raise HTTPException(404, "Utente non trovato")
    percorso = _salva_foto(user_id, "partner_ideale", file)
    cur.execute("UPDATE physical_profile SET foto_partner_ideale_url = %s WHERE user_id = %s",
                (percorso, str(user_id)))
    esito_moderazione = _modera_foto(cur, user_id, "Foto partner ideale", percorso,
                                      os.path.join(STORAGE_DIR, percorso))
    conn.commit()
    conn.close()
    return {"foto_partner_ideale_url": percorso, "embedding_calcolato": False, "esito_moderazione": esito_moderazione}
