"""RF-32d: endpoint interno per il motore di scheduling dell'engagement
(v. CLAUDE.md, services/engagement_scheduler.py). Sostituisce un Render Cron
Job dedicato — fatturato al minuto anche per esecuzioni brevi, minimo $1/
mese, un costo evitabile qui — con l'approccio gratuito già scelto
dall'utente: un endpoint protetto richiamato una volta al giorno da una
GitHub Action schedulata (.github/workflows/engagement-cron.yml), che gira
sui runner gratuiti di GitHub e sveglia il servizio Free di Render con una
semplice richiesta HTTP.

Protezione: header X-Cron-Secret confrontato a tempo costante
(secrets.compare_digest, stesso principio già usato per l'HTTP Basic Auth
del pannello admin, v. routers/admin_viewer.py) con la variabile d'ambiente
CRON_SECRET — mai hardcoded, mai loggata. Il secret vero vive come GitHub
Secret del repository, mai in chiaro nel workflow YAML."""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from db import get_conn
from services.engagement_scheduler import esegui

router = APIRouter(prefix="/internal/cron", tags=["internal-cron"])


def verifica_cron_secret(x_cron_secret: str = Header(default="")) -> None:
    atteso = os.environ.get("CRON_SECRET", "")
    if not atteso or not secrets.compare_digest(x_cron_secret, atteso):
        raise HTTPException(401, "Secret non valido")


@router.post("/engagement-daily", dependencies=[Depends(verifica_cron_secret)])
def engagement_daily():
    """Eseguito una volta al giorno dalla GitHub Action. dry_run=False
    fisso: a differenza dello script CLI (che ha --live come flag esplicito
    per sicurezza durante i test manuali), questo endpoint esiste solo per
    essere chiamato dallo scheduler reale, sempre in modalità scrittura."""
    conn = get_conn()
    risultati = esegui(conn, dry_run=False)
    conn.close()
    # Risposta compatta (conteggi per esito, non l'elenco per-utente — fino
    # a migliaia di righe non hanno senso nella risposta HTTP di un cron).
    # "generazione_pillola" è un singolo dict (un'azione globale per run,
    # non per-utente) — riportato così com'è, non aggregato come gli altri.
    riepilogo = {"generazione_pillola": risultati.pop("generazione_pillola", None)}
    for tipo, righe in risultati.items():
        conteggi = {}
        for r in righe:
            conteggi[r["esito"]] = conteggi.get(r["esito"], 0) + 1
        riepilogo[tipo] = {"eleggibili": len(righe), "per_esito": conteggi}
    return riepilogo
