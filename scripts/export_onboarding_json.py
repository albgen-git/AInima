"""RF-25h: esportazione consolidata delle risposte di onboarding di un
utente — CLI, uso manuale su richiesta. Logica condivisa con il trigger
automatico al completamento onboarding (routers/auth.py) in
backend/services/onboarding_export.py — v. quel modulo per i dettagli
(cosa contiene/non contiene, convenzione R2, campi esclusi).

Generico (funziona per qualunque utente passando --user-id o --email).

Uso:
    python scripts/export_onboarding_json.py --email albgen@gmail.com --render
    python scripts/export_onboarding_json.py --user-id <uuid> [--render]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.onboarding_export import costruisci_export, trova_campi_mancanti, upload_r2  # noqa: E402


def _connetti(usa_render: bool):
    if usa_render:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    from db import get_conn  # noqa: E402

    return get_conn()


def _risolvi_user_id(cur, user_id: str | None, email: str | None) -> str:
    if user_id:
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    else:
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    riga = cur.fetchone()
    if not riga:
        raise SystemExit(f"Nessun utente trovato per user_id={user_id!r} email={email!r}")
    return str(riga["user_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id")
    parser.add_argument("--email")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    if not args.user_id and not args.email:
        raise SystemExit("Serve --user-id o --email")

    conn = _connetti(args.render)
    cur = conn.cursor()
    user_id = _risolvi_user_id(cur, args.user_id, args.email)
    export = costruisci_export(cur, user_id)
    conn.close()

    url = upload_r2(user_id, export)

    mancanti = trova_campi_mancanti(export)
    print(f"user_id: {user_id}")
    print(f"Caricato su R2: {url}")
    print(f"\nCampi NULL/mancanti trovati ({len(mancanti)}):")
    for m in mancanti:
        print(f"  - {m}")


if __name__ == "__main__":
    main()
