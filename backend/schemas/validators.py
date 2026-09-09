"""Validatori Pydantic condivisi tra più schemi."""

from email_validator import EmailNotValidError, validate_email


def valida_email_deliverable(v: str) -> str:
    """EmailStr da sola verifica solo la sintassi — un dominio scritto
    male ma sintatticamente plausibile (es. "gmai.cox" invece di
    "gmail.com") viene accettato in silenzio: l'OTP non arriva mai a
    nessuno, e chi si è registrato non capisce perché (segnalato
    dall'utente da un test reale, v. CLAUDE.md). Aggiunge un controllo
    di deliverability (il dominio esiste davvero, via DNS) sopra la
    sintassi già garantita da EmailStr."""
    try:
        validate_email(v, check_deliverability=True)
    except EmailNotValidError:
        raise ValueError(
            "L'indirizzo email inserito non è valido — controlla di averlo scritto correttamente"
        )
    return v
