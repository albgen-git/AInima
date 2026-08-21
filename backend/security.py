"""Hashing OTP + token di sessione.

Hashing: PBKDF2-HMAC-SHA256 dalla libreria standard (nessuna dipendenza
nativa da compilare, a differenza di bcrypt su questo ambiente Windows
senza toolchain C++, v. CLAUDE.md nota su pgvector). Non più usato per
password (RF-02, Documento_Requisiti_v1_2.md: autenticazione via email
OTP, nessuna password permanente) — riusato per hashare i codici OTP
prima di salvarli a DB, stesso principio: mai in chiaro a riposo.

Token di sessione: JWT firmato HS256. Emesso alla verifica OTP riuscita,
ma NON ancora richiesto/verificato su nessun'altra rotta dell'app (v.
CLAUDE.md) — build block per un'estensione futura, non applicato oggi.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

ITERAZIONI = 260_000


def _hash_secret(valore: str) -> str:
    salt = os.urandom(16)
    derivato = hashlib.pbkdf2_hmac("sha256", valore.encode(), salt, ITERAZIONI)
    return f"{salt.hex()}${derivato.hex()}"


def _verify_secret(valore: str, hash_salvato: str) -> bool:
    try:
        salt_hex, derivato_hex = hash_salvato.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    derivato_atteso = bytes.fromhex(derivato_hex)
    derivato = hashlib.pbkdf2_hmac("sha256", valore.encode(), salt, ITERAZIONI)
    return hmac.compare_digest(derivato, derivato_atteso)


def hash_otp(codice: str) -> str:
    """Codice OTP a 6 cifre — mai salvato in chiaro (v. CLAUDE.md)."""
    return _hash_secret(codice)


def verify_otp_hash(codice: str, hash_salvato: str) -> bool:
    return _verify_secret(codice, hash_salvato)


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY non impostata — obbligatoria per emettere token di sessione, v. .env.example"
        )
    return secret


def create_session_token(user_id: UUID, scadenza_giorni: int) -> str:
    scadenza = datetime.now(timezone.utc) + timedelta(days=scadenza_giorni)
    payload = {"sub": str(user_id), "exp": scadenza}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_session_token(token: str) -> UUID | None:
    """Pronta per quando il token verrà davvero richiesto sulle altre rotte
    (v. nota in cima al file) — non ancora chiamata da nessun endpoint oggi."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
