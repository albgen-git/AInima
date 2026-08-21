"""RF-25/25b: pannello di back-office — ricerca profili, config, metriche."""

from typing import Optional

from pydantic import BaseModel


class SystemConfigOut(BaseModel):
    chiave: str
    valore: str
    descrizione: Optional[str]


class SystemConfigUpdate(BaseModel):
    valore: str


class MetricsOut(BaseModel):
    totale_iscritti: int
    utenti_attivi: int
    match_proposti: int
    match_confermati: int
    tasso_conversione_pct: float
    rapporto_genere: dict


class AccountStatusUpdate(BaseModel):
    stato_account: str
