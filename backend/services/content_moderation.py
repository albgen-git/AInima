"""RF-06b/RNF-09: moderazione automatica dei contenuti fotografici,
interfaccia astratta come EmailProvider (services/email_provider.py) — per
poter collegare un provider (AWS Rekognition / Google Cloud Vision
SafeSearch / Azure Content Safety / altro) senza toccare le rotte.

Nessun provider ancora scelto (decisione rimandata esplicitamente
dall'utente, v. CLAUDE.md 2026-08-19) — NullContentModerationProvider è
l'implementazione di default: NON blocca l'onboarding (esito 'In errore',
non 'Sospetta' — solo una scansione realmente sospetta mette l'account in
attesa di revisione, un fallimento/assenza di scansione no, per non
introdurre attrito quando non c'è ancora un provider configurato, v.
RNF-09). Sostituire con un provider reale quando scelto."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RisultatoModerazione:
    esito: str  # 'OK' | 'Sospetta' | 'In errore'
    score_confidenza: float | None = None


class ContentModerationProvider(ABC):
    @abstractmethod
    def analizza(self, riferimento_immagine: str) -> RisultatoModerazione:
        """`riferimento_immagine`: path relativo su storage locale o URL
        assoluto su R2 (v. services/photo_storage.py) — non più garantito
        un path assoluto sul filesystem del processo, dato che il piano
        gratuito Render ha disco effimero (v. CLAUDE.md). Un provider reale
        (AWS Rekognition/GCV SafeSearch/ecc.) leggerà i byte dal file
        locale o scaricherà dall'URL a seconda del caso."""
        ...


class NullContentModerationProvider(ContentModerationProvider):
    def analizza(self, riferimento_immagine: str) -> RisultatoModerazione:
        return RisultatoModerazione(esito="In errore", score_confidenza=None)


_provider = None


def get_content_moderation_provider() -> ContentModerationProvider:
    global _provider
    if _provider is None:
        nome = os.environ.get("CONTENT_MODERATION_PROVIDER", "none")
        if nome == "none":
            _provider = NullContentModerationProvider()
        else:
            raise RuntimeError(f"Provider di moderazione contenuti sconosciuto: '{nome}'")
    return _provider
