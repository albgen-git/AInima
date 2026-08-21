"""Migrazione live per l'allineamento ai documenti aggiornati (v.
CLAUDE.md 2026-08-19): rimozione chat-intervista LLM, test attaccamento/EQ
scritti, moderazione contenuti, cambio email/recupero accesso, matching a
similarità vettoriale pura. Nessun Alembic nel progetto — pattern ad-hoc
già usato per le migrazioni precedenti.

Uso: python scripts/migrate_2026_08_19_allineamento_requisiti.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402


def main():
    conn = get_conn()
    conn.autocommit = True  # ALTER TYPE ... ADD VALUE non può girare in una transazione
    cur = conn.cursor()

    print("1. stato_account_enum: aggiungo 'In attesa - verifica moderazione'...")
    cur.execute("ALTER TYPE stato_account_enum ADD VALUE IF NOT EXISTS 'In attesa - verifica moderazione'")

    conn.autocommit = False

    print("2. psychometric_scores: rimuovo colonne superate, aggiungo le nuove...")
    cur.execute("""
        ALTER TABLE psychometric_scores
            DROP COLUMN IF EXISTS attaccamento_probabilita,
            DROP COLUMN IF EXISTS red_flags_rilevati,
            DROP COLUMN IF EXISTS incongruenze_test_intervista,
            DROP COLUMN IF EXISTS transcript_id,
            DROP COLUMN IF EXISTS chat_transcript,
            DROP COLUMN IF EXISTS chat_eq_completata_il,
            DROP COLUMN IF EXISTS richiede_revisione_umana,
            ADD COLUMN IF NOT EXISTS ansia_score REAL,
            ADD COLUMN IF NOT EXISTS evitamento_score REAL,
            ADD COLUMN IF NOT EXISTS stile_attaccamento VARCHAR(30)
    """)

    print("3. Nuove tabelle: profile_narrative, content_moderation_log, email_change_requests...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile_narrative (
            user_id                     UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            descrizione_di_se           TEXT,
            descrizione_partner_ideale  TEXT,
            data_ultima_modifica        TIMESTAMPTZ
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS content_moderation_log (
            moderation_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            tipo_immagine           VARCHAR(20) NOT NULL,
            immagine_url             VARCHAR(255) NOT NULL,
            esito_automatico          VARCHAR(15) NOT NULL DEFAULT 'In errore',
            score_confidenza          REAL,
            data_scansione             TIMESTAMPTZ NOT NULL DEFAULT now(),
            esito_revisione_umana      VARCHAR(15) NOT NULL DEFAULT 'In attesa',
            revisionato_da              UUID,
            data_revisione               TIMESTAMPTZ
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_change_requests (
            request_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                       UUID REFERENCES users(user_id) ON DELETE CASCADE,
            email_attuale_dichiarata       VARCHAR(255),
            email_nuova_richiesta           VARCHAR(255) NOT NULL,
            dati_identificativi_forniti      JSONB,
            origine                          VARCHAR(40) NOT NULL,
            stato                            VARCHAR(25) NOT NULL DEFAULT 'In attesa revisione',
            revisionato_da                    UUID,
            data_richiesta                     TIMESTAMPTZ NOT NULL DEFAULT now(),
            data_decisione                      TIMESTAMPTZ,
            data_scadenza_grazia                 TIMESTAMPTZ,
            token_annullamento                    VARCHAR(255)
        )
    """)

    print("4. Righe vuote in profile_narrative per gli utenti esistenti (stesso pattern delle altre tabelle satellite)...")
    cur.execute("""
        INSERT INTO profile_narrative (user_id)
        SELECT user_id FROM users
        WHERE user_id NOT IN (SELECT user_id FROM profile_narrative)
    """)

    print("5. system_config: rinomino/aggiungo/rimuovo parametri...")
    cur.execute("UPDATE system_config SET chiave = 'report_top_candidates', "
                "descrizione = %s WHERE chiave = 'matching_stage2_pool_size'",
                ("Numero di candidati migliori per cui pre-generare un report testuale (Prompt 5) — non influenza il calcolo dei punteggi",))
    cur.execute("DELETE FROM system_config WHERE chiave = 'soglia_tie_break_visivo'")
    cur.execute("""
        INSERT INTO system_config (chiave, valore, descrizione) VALUES
            ('dimensione_shortlist_analisi_visiva', '5', 'Numero di candidati Top N per compatibilità caratteriale tra cui scegliere per somiglianza visiva (RF-11a/RF-11b), se la foto "partner ideale" è presente'),
            ('weight_eq_autoconsapevolezza',   '0.25', 'Peso del pilastro Autoconsapevolezza in score_maturita_emotiva (Ainima_Test_EQScore_v1.md)'),
            ('weight_eq_autoregolazione',      '0.25', 'Peso del pilastro Autoregolazione in score_maturita_emotiva'),
            ('weight_eq_empatia',              '0.25', 'Peso del pilastro Empatia in score_maturita_emotiva'),
            ('weight_eq_responsabilita',       '0.25', 'Peso del pilastro Responsabilità relazionale in score_maturita_emotiva'),
            ('recupero_accesso_grazia_ore',    '48',   'Ore del periodo di grazia dopo l''approvazione di un cambio email, entro cui la vecchia email può annullare (RF-26d)')
        ON CONFLICT (chiave) DO NOTHING
    """)
    cur.execute("""
        UPDATE system_config SET descrizione = 'Peso w3 Coerenza Narrativa (similarità vettoriale, non più LLM) nel FINAL_SCORE'
        WHERE chiave = 'weight_narrativa'
    """)

    print("6. matching_algorithm_versions: aggiungo stable_v2/stable_v3...")
    cur.execute("""
        INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
            ('stable_v2', 'Come stable_v1, con la distanza non più un tetto fisso in km ma un fattore condizionale su importanza_vicinanza_geografica + lingue_parlate oltre la soglia urbana (Ainima_Algoritmo_Ranking_Finale_v1.md §3bis).'),
            ('stable_v3', 'Allineamento ai documenti aggiornati dopo la sessione con lo psicologo (v. CLAUDE.md): (a) attaccamento da formula continua ansia/evitamento invece della matrice 4x4 su etichette LLM; (b) Coerenza Narrativa da similarità vettoriale pura tra self/ideal embedding, Judge LLM Prompt 4 eliminato; (c) filtro hard su flag_profilo_per_revisione_dati al posto di red_flags_rilevati; (d) selezione per somiglianza visiva sempre applicata sulla shortlist, non più solo come tie-break tra quasi pari.')
        ON CONFLICT (versione) DO NOTHING
    """)

    conn.commit()
    conn.close()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
