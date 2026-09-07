"""Torneo estetico — spareggio secondario tramite preferenza estetica
(v. CLAUDE.md 2026-09-06). 8 partecipanti, 7 confronti a bracket."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Posizione = Literal["A", "B", "C", "D", "E", "F", "G", "H"]


class Partecipante(BaseModel):
    posizione: Posizione
    cluster_id: UUID
    foto_url: str


class TorneoInizio(BaseModel):
    sessione_id: UUID
    partecipanti: list[Partecipante]


class ConfrontoIn(BaseModel):
    sessione_id: UUID
    turno: int  # 1, 2 o 3
    cluster_id_a: UUID
    cluster_id_b: UUID
    cluster_id_vincitore: UUID


class ConfrontoOut(BaseModel):
    completato: bool
    cluster_id_vincitore_torneo: UUID | None = None
    foto_preferenza_urls: list[str] | None = None


class PreferenzaEsteticaOut(BaseModel):
    """GET di stato — permette al frontend di distinguere "mai fatto il
    torneo" da "già fatto, ecco il risultato" senza dover rilanciare il
    torneo per scoprirlo."""

    completato: bool
    data_completamento: datetime | None = None
    foto_preferenza_urls: list[str] | None = None
