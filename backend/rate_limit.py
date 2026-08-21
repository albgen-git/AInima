"""Rate limiting IP-based per /auth/request-otp — finestra scorrevole in
memoria, stesso principio già usato in precedenza per lo store OTP telefono
(ora rimosso). Sufficiente per un singolo processo MVP; non sopravvive a un
riavvio né funziona across più processi — nota, non bloccante per questa
fase (v. CLAUDE.md)."""

import time
from collections import defaultdict

_richieste_per_ip: dict[str, list[float]] = defaultdict(list)


def controlla_e_registra(ip: str, limite: int, finestra_secondi: int = 3600) -> bool:
    """Ritorna True se la richiesta è ammessa (e la registra), False se il
    limite è già stato raggiunto in questa finestra temporale."""
    ora = time.time()
    richieste = _richieste_per_ip[ip]
    richieste[:] = [t for t in richieste if ora - t < finestra_secondi]
    if len(richieste) >= limite:
        return False
    richieste.append(ora)
    return True
