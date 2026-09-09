"""Validatori Pydantic condivisi tra più schemi."""

from email_validator import EmailNotValidError, validate_email

# RF-06c/§7.3: stessi 195 codici ISO 3166-1 alpha-2 del dropdown frontend
# (frontend/src/lib/countries.ts, stati membri/osservatori ONU) — tenuti
# sincronizzati a mano tra i due file (nessun modo semplice di condividere
# un'unica fonte tra Python e TypeScript in questo progetto). Un controllo
# di solo formato ("2 lettere maiuscole") accetterebbe codici inesistenti
# (es. "XX") che il dropdown non produrrebbe mai ma una chiamata diretta
# all'API sì — la whitelist reale chiude anche quel varco.
CODICI_PAESE_VALIDI = {
    "AF", "AL", "DZ", "AD", "AO", "AG", "AR", "AM", "AU", "AT", "AZ", "BS", "BH", "BD", "BB",
    "BY", "BE", "BZ", "BJ", "BT", "BO", "BA", "BW", "BR", "BN", "BG", "BF", "BI", "KH", "CM",
    "CA", "CV", "TD", "CL", "CN", "CY", "VA", "CO", "KM", "KP", "KR", "CI", "CR", "HR", "CU",
    "DK", "DM", "EC", "EG", "SV", "AE", "ER", "EE", "SZ", "ET", "FJ", "PH", "FI", "FR", "GA",
    "GM", "GE", "DE", "GH", "JM", "JP", "GI", "DJ", "JO", "GR", "GD", "GT", "GN", "GW", "GQ",
    "GY", "HT", "HN", "HK", "IN", "ID", "IR", "IQ", "IE", "IS", "IL", "IT", "KZ", "KE", "KG",
    "KI", "KW", "LA", "LS", "LV", "LB", "LR", "LY", "LI", "LT", "LU", "MO", "MG", "MW", "MV",
    "MY", "ML", "MT", "MA", "MH", "MR", "MU", "MX", "MD", "MC", "MN", "ME", "MZ", "MM", "NA",
    "NR", "NP", "NI", "NE", "NG", "NO", "NZ", "OM", "NL", "PK", "PW", "PS", "PA", "PG", "PY",
    "PE", "PL", "PT", "QA", "GB", "CZ", "CF", "CD", "CG", "DO", "RO", "RW", "RU", "EH", "KN",
    "LC", "VC", "WS", "SM", "ST", "SN", "RS", "SC", "SL", "SG", "SY", "SK", "SI", "SO", "ES",
    "LK", "US", "ZA", "SD", "SS", "SE", "CH", "SR", "TJ", "TW", "TZ", "TH", "TL", "TG", "TO",
    "TT", "TN", "TR", "TM", "TV", "UA", "UG", "HU", "UY", "UZ", "VU", "VE", "VN", "YE", "ZM",
    "ZW",
}


def valida_paese_residenza(v: str | None) -> str | None:
    """RF-06c: codice ISO 3166-1 alpha-2 — whitelist reale, non solo
    formato, per non accettare codici inesistenti da una chiamata diretta
    all'API che bypassa il dropdown."""
    if v is None:
        return v
    v = v.upper()
    if v not in CODICI_PAESE_VALIDI:
        raise ValueError(
            f"Codice paese non valido: {v!r} — deve essere un codice ISO 3166-1 alpha-2 (es. 'IT', 'AE')"
        )
    return v


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
