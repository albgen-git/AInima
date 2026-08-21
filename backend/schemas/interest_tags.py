"""RF-08c: liste "Mi Piace/Non Sopporto" e "Partner Vorrei/Non Vorrei" —
v. docs/Ainima_Liste_Piace_Detesta_v1.md."""

from typing import Optional

from pydantic import BaseModel


class InterestTagsUpdate(BaseModel):
    """Testo libero corto, separato da virgola (es. "gatti, montagna,
    cucina") — non narrativa, nessuna delle regole anti-prompt-injection
    delle descrizioni libere si applica qui con lo stesso peso (liste
    corte, non conversazione), ma restano comunque solo dato da tokenizzare
    e incorporare, mai istruzioni."""
    mi_piace: Optional[str] = None
    non_sopporto: Optional[str] = None
    partner_vorrei: Optional[str] = None
    partner_non_vorrei: Optional[str] = None


class InterestTagsOut(BaseModel):
    mi_piace: Optional[str]
    non_sopporto: Optional[str]
    partner_vorrei: Optional[str]
    partner_non_vorrei: Optional[str]
    mi_piace_tags: Optional[list[str]]
    non_sopporto_tags: Optional[list[str]]
    partner_vorrei_tags: Optional[list[str]]
    partner_non_vorrei_tags: Optional[list[str]]
