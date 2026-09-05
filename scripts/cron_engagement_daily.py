"""RF-32d: thin wrapper CLI su services/engagement_scheduler.py — stesso
pattern già in uso per scripts/export_onboarding_json.py/
services/onboarding_export.py (v. CLAUDE.md): la logica vera vive nel
service condiviso, riusata sia da qui (rilanci manuali da locale) sia
dall'endpoint HTTP protetto POST /internal/cron/engagement-daily
(routers/internal_cron.py, chiamato quotidianamente dalla GitHub Action
.github/workflows/engagement-cron.yml — NON un Render Cron Job, per
evitare il costo minimo del piano Starter richiesto per quel servizio).

Uso:
    python scripts/cron_engagement_daily.py            (DB locale, dry-run)
    python scripts/cron_engagement_daily.py --live      (DB locale, scrive davvero)
    python scripts/cron_engagement_daily.py --render --live   (DB Render, per test manuale da locale)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _connetti(usa_render: bool):
    if usa_render:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    from db import get_conn  # noqa: E402

    return get_conn()


def main():
    from services.engagement_scheduler import esegui  # noqa: E402

    usa_render = "--render" in sys.argv
    dry_run = "--live" not in sys.argv  # default dry-run per sicurezza — serve --live per scrivere davvero
    conn = _connetti(usa_render)
    risultati = esegui(conn, dry_run=dry_run)
    conn.close()

    print(f"\n=== Generazione pillola del giorno (dry_run={dry_run}) ===")
    print(" ", risultati.pop("generazione_pillola", None))

    for tipo, righe in risultati.items():
        print(f"\n=== {tipo} ({len(righe)} utenti eleggibili, dry_run={dry_run}) ===")
        for r in righe:
            print(" ", r)


if __name__ == "__main__":
    main()
