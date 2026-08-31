"""Migrazione live: Report di analisi personale (RF-28..RF-30b, §7.11/
§7.12 — v. CLAUDE.md). Crea le 2 nuove tabelle personal_report/
personal_report_feedback, idempotente (CREATE TABLE/INDEX IF NOT EXISTS,
sicuro da rilanciare).

Uso: python scripts/migrate_2026_08_31_personal_report.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

SQL = """
CREATE TABLE IF NOT EXISTS personal_report (
    report_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    contenuto_report       TEXT NOT NULL,
    data_generazione        TIMESTAMPTZ NOT NULL DEFAULT now(),
    email_inviata            BOOLEAN NOT NULL DEFAULT FALSE,
    data_invio_email          TIMESTAMPTZ,
    versione                   INT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_personal_report_user ON personal_report(user_id, versione DESC);

CREATE TABLE IF NOT EXISTS personal_report_feedback (
    feedback_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id              UUID NOT NULL REFERENCES personal_report(report_id) ON DELETE CASCADE,
    user_id                 UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    valutazione_stelle        SMALLINT NOT NULL CHECK (valutazione_stelle BETWEEN 1 AND 5),
    commento_libero            TEXT,
    data_feedback                TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_id, user_id)
);
"""


def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    print("personal_report / personal_report_feedback: create (o già presenti).")
    conn.close()


if __name__ == "__main__":
    main()
