"""Invio email transazionali (solo OTP per ora, RF-02) — astratto dietro
un'interfaccia (`EmailProvider`) così cambiare provider in futuro non
tocca `routers/auth.py`, solo questo file. Provider scelto per l'MVP:
Resend (tier gratuito 100 email/giorno, nessun legame con AWS/altri cloud,
utilizzabile da subito in locale — v. CLAUDE.md per il confronto con le
alternative valutate)."""

import os
from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    def invia_otp(self, email: str, codice: str) -> None:
        """Deve sollevare un'eccezione se l'invio fallisce — il chiamante
        (routers/auth.py) decide come reagire, non questo layer."""
        raise NotImplementedError

    @abstractmethod
    def invia_notifica(self, email: str, oggetto: str, corpo_html: str) -> None:
        """Email di sicurezza/informativa generica (non un OTP) — usata per
        RF-26 (notifica cambio email alla vecchia casella) e RF-26d (link
        di annullamento/completamento del recupero accesso)."""
        raise NotImplementedError


class ResendEmailProvider(EmailProvider):
    def __init__(self):
        import resend

        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key:
            raise RuntimeError(
                "RESEND_API_KEY non impostata — v. .env.example. Senza, "
                "l'invio OTP via email non può funzionare."
            )
        resend.api_key = api_key
        self._resend = resend
        self._from = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    def invia_otp(self, email: str, codice: str) -> None:
        self._resend.Emails.send(
            {
                "from": self._from,
                "to": [email],
                "subject": "Il tuo codice di accesso Ainima",
                "html": (
                    f"<p>Il tuo codice di accesso è:</p>"
                    f"<p style='font-size:28px;font-weight:600;letter-spacing:4px'>{codice}</p>"
                    f"<p>Scade tra pochi minuti. Se non hai richiesto questo codice, ignora questa email.</p>"
                ),
            }
        )

    def invia_notifica(self, email: str, oggetto: str, corpo_html: str) -> None:
        self._resend.Emails.send({"from": self._from, "to": [email], "subject": oggetto, "html": corpo_html})


_provider: EmailProvider | None = None


def get_email_provider() -> EmailProvider:
    """Factory che legge EMAIL_PROVIDER (default 'resend') — punto unico da
    estendere quando si aggiungerà un secondo provider in futuro."""
    global _provider
    if _provider is None:
        nome = os.environ.get("EMAIL_PROVIDER", "resend").lower()
        if nome == "resend":
            _provider = ResendEmailProvider()
        else:
            raise RuntimeError(f"EMAIL_PROVIDER '{nome}' non supportato")
    return _provider
