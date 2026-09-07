"""Migrazione live: Torneo estetico (spareggio secondario tramite
preferenza estetica), nuova feature — v. CLAUDE.md 2026-09-06.

Crea:
- torneo_estetico_cluster: rappresentanti del clustering offline (MVP:
  estrazione casuale, 8 per genere).
- torneo_estetico_confronti: log di ogni singolo confronto del torneo.
- preferenza_estetica_utente: risultato finale per utente (10 foto).
- matches.selezionato_per_torneo_estetico (bool, come selezionato_per_
  somiglianza_visiva già esistente).
- system_config.soglia_pareggio_final_score (default 0.03).

Idempotente (CREATE TABLE/ADD COLUMN IF NOT EXISTS, INSERT ON CONFLICT).

Uso:
    python scripts/migrate_2026_09_06_torneo_estetico.py            (DB locale)
    python scripts/migrate_2026_09_06_torneo_estetico.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

SQL = """
ALTER TABLE matches ADD COLUMN IF NOT EXISTS selezionato_per_torneo_estetico BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS torneo_estetico_cluster (
    cluster_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    genere               genere_enum NOT NULL,
    foto_url               VARCHAR(255) NOT NULL,
    source_actor_id         INT,
    metodo_selezione         VARCHAR(20) NOT NULL DEFAULT 'casuale_mvp',
    data_creazione            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS torneo_estetico_confronti (
    confronto_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sessione_id           UUID NOT NULL,
    turno                  SMALLINT NOT NULL,
    cluster_id_a             UUID NOT NULL REFERENCES torneo_estetico_cluster(cluster_id),
    cluster_id_b             UUID NOT NULL REFERENCES torneo_estetico_cluster(cluster_id),
    cluster_id_vincitore      UUID NOT NULL REFERENCES torneo_estetico_cluster(cluster_id),
    data_confronto             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS preferenza_estetica_utente (
    user_id               UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    cluster_id_vincitore    UUID NOT NULL REFERENCES torneo_estetico_cluster(cluster_id),
    foto_preferenza_urls      TEXT[] NOT NULL,
    data_completamento         TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO system_config (chiave, valore, descrizione) VALUES
    ('soglia_pareggio_final_score', '0.03',
     'Torneo estetico: differenza massima di FINAL_SCORE tra candidati perche'' siano considerati "quasi pari" e attivino lo spareggio secondario')
ON CONFLICT (chiave) DO NOTHING;

INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v12', 'Torneo estetico (RF nuova, v. CLAUDE.md 2026-09-06): spareggio secondario indipendente da RF-11a/b, attivo solo quando due o piu'' candidati sono quasi pari per FINAL_SCORE (entro soglia_pareggio_final_score) — riordina il prefisso pareggiato per similarita'' media tra le foto profilo dei candidati e le 10 foto di preferenza estetica del cercatore, derivate da un torneo a confronti (services/matching_engine.py::applica_spareggio_estetico).')
ON CONFLICT (versione) DO NOTHING;
"""


def main():
    if "--render" in sys.argv:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        from db import get_conn  # noqa: E402

        conn = get_conn()

    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    print("Torneo estetico: tabelle/colonne/config pronte.")
    conn.close()


if __name__ == "__main__":
    main()
