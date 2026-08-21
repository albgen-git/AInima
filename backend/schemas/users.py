"""Modelli Pydantic per autenticazione, profilo, contatti — v.
Documento_Requisiti_v1_2.md §4.1, §7.1-7.3 (autenticazione via email OTP,
non più email+password — v. CLAUDE.md)."""

from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

Genere = Literal["Maschile", "Femminile", "Non binario", "Altro"]
Orientamento = Literal["Eterosessuale", "Omosessuale", "Bisessuale", "Pansessuale", "Asessuale", "Altro"]
StatoAccount = Literal["In attesa", "Attivo", "Sospeso", "Chiuso"]


class RequestOtpRequest(BaseModel):
    """RF-02: primo contatto per un utente nuovo O di ritorno — stessa
    richiesta per entrambi i casi, la risposta non rivela mai quale dei
    due si tratti (anti user-enumeration)."""
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    codice: str = Field(min_length=6, max_length=6)


class VerifyOtpResponse(BaseModel):
    user_id: UUID
    stato_account: StatoAccount
    token: str


class PaymentMethodRequest(BaseModel):
    """RF-03/04: registrazione carta + pre-autorizzazione simbolica.
    Il token arriva già tokenizzato dal client (Stripe Elements o
    equivalente) — nessun dato di carta in chiaro transita da qui, come
    da RNF-06. L'integrazione col gateway non è implementata (stub)."""
    metodo_pagamento_token: str


class ProfileUpdate(BaseModel):
    """RF-06: profilo anagrafico/fisico + socio-economico (§7.2-7.3).
    Include anche i campi identità (nome/cognome/data_nascita/genere/
    telefono) e i dati particolari (orientamento_sessuale, dietro
    consenso_dati_sensibili) — con l'autenticazione via email OTP
    l'account nasce con la sola email, il resto si compila progressivamente
    negli step successivi del wizard tramite questo stesso endpoint
    (v. CLAUDE.md)."""
    nome: Optional[str] = None
    cognome: Optional[str] = None
    data_nascita: Optional[date] = None
    genere: Optional[Genere] = None
    # autodichiarato, MAI verificato in questa fase (RF-02b)
    telefono: Optional[str] = None
    # dato particolare ex art. 9 GDPR — il frontend lo invia solo dopo lo
    # step di consenso esplicito, ma consenso_dati_sensibili è comunque
    # rivalidato qui: non ci si fida del solo gate lato client.
    orientamento_sessuale: Optional[Orientamento] = None
    consenso_dati_sensibili: Optional[bool] = None
    altezza_cm: Optional[int] = None
    peso_kg: Optional[float] = None
    corporatura: Optional[str] = None
    colore_capelli: Optional[str] = None
    colore_occhi: Optional[str] = None
    fumo: Optional[bool] = None
    alcol: Optional[bool] = None
    stile_vita_sport: Optional[str] = None
    comune_residenza: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    titolo_studio: Optional[str] = None
    settore_occupazionale: Optional[str] = None
    fascia_reddito: Optional[str] = None
    fede_religiosa: Optional[str] = None
    importanza_religione: Optional[int] = Field(default=None, ge=1, le=5)
    stato_civile: Optional[str] = None
    ha_figli: Optional[bool] = None
    # v. Ainima_Algoritmo_Ranking_Finale_v1.md §3bis/§9 — sostituiscono
    # pref_distanza_max_km (superato) per le coppie oltre soglia_area_urbana_km.
    # importanza_vicinanza_geografica arriva come Likert 1-5 grezzo dal client,
    # normalizzato 0.0-1.0 nel router (stessa convenzione dei punteggi Big Five).
    importanza_vicinanza_geografica: Optional[int] = Field(default=None, ge=1, le=5)
    lingue_parlate: Optional[list[str]] = None

    @field_validator("consenso_dati_sensibili")
    @classmethod
    def valida_consenso(cls, v: Optional[bool]) -> Optional[bool]:
        if v is False:
            raise ValueError(
                "È necessario il consenso esplicito al trattamento dei dati "
                "particolari (art. 9 GDPR) — non può essere revocato inviando 'false' qui"
            )
        return v


class UserOut(BaseModel):
    user_id: UUID
    nome: Optional[str]
    cognome: Optional[str]
    email: str
    genere: Optional[Genere]
    orientamento_sessuale: Optional[Orientamento]
    stato_account: StatoAccount
    data_creazione: datetime

    class Config:
        from_attributes = True
