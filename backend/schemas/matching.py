"""RF-10..RF-24: proposta di match, accettazione/rifiuto, feedback."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

StatoMatch = Literal["Proposto", "Accettato_A", "Accettato_B", "Confermato", "Rifiutato", "Scaduto"]


class ProposalOut(BaseModel):
    """RF-12: la proposta è mostrata in forma anonima — nessun nome/cognome/
    contatto finché il match non è Confermato."""
    match_id: UUID
    stato: StatoMatch
    eta: int
    genere: str
    corporatura: Optional[str]
    titolo_studio: Optional[str]
    foto_profilo_url: Optional[str]
    distanza_km: Optional[float]
    data_scadenza_risposta: Optional[datetime]
    in_attesa_di_te: bool
    """True se questo utente deve ancora rispondere (stato='Proposto', oppure
    stato='Accettato_<lato altrui>'). Necessario perché 'Accettato_A'/
    'Accettato_B' da soli sono ambigui lato frontend: la proposta è anonima
    e non espone mai quale lato (A/B) corrisponda a questo utente."""


class MatchDecision(BaseModel):
    accetta: bool


class MatchOut(BaseModel):
    match_id: UUID
    stato: StatoMatch
    final_score: Optional[float]
    data_proposta: datetime
    data_scadenza_risposta: Optional[datetime]
    contatto_scambiato: bool

    class Config:
        from_attributes = True


class FeedbackIn(BaseModel):
    """RF-23/24: raccolto 15gg dopo la chiusura del task."""
    esito: str
    note_libere: Optional[str] = None


class RubricaEntry(BaseModel):
    """RF-22b: elenco degli abbinamenti conclusi, con vCard riscaricabile."""
    match_id: UUID
    nome: str
    cognome: str
    foto_profilo_url: Optional[str]
    data_conferma: Optional[datetime]
