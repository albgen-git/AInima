"""RF-26/26b/26c/26d: cambio email self-service + recupero accesso pubblico."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class EmailChangeRequestIn(BaseModel):
    """RF-26: richiesta di cambio email da account già autenticato."""
    email_nuova: EmailStr


class EmailChangeConfirmIn(BaseModel):
    """RF-26: verifica OTP inviato alla NUOVA email."""
    codice: str


class RecoveryRequestIn(BaseModel):
    """RF-26b: modulo pubblico, non autenticato. Nessun dato di carta
    completo — solo le ultime 4 cifre, mai il numero intero (RNF-06)."""
    email_attuale_dichiarata: Optional[EmailStr] = None
    email_nuova_richiesta: EmailStr
    nome: Optional[str] = None
    cognome: Optional[str] = None
    data_nascita: Optional[str] = None
    citta: Optional[str] = None
    ultime4cifre_carta: Optional[str] = None


class RecoveryDecisionIn(BaseModel):
    """RF-25d: decisione dello staff sulla coda di recupero accesso."""
    approvato: bool
    user_id: Optional[UUID] = None  # richiesto se approvato: quale account è
    revisionato_da: Optional[UUID] = None


class ModerationDecisionIn(BaseModel):
    """RF-25c: decisione dello staff sulla coda di moderazione contenuti."""
    approvato: bool
    revisionato_da: Optional[UUID] = None
