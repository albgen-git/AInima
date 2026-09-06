"""Migrazione live: rinomina la chiave system_config
finestra_risposta_match_giorni -> finestra_giorni_risposta_match.

Allinea alla convenzione di naming di Documento_Requisiti_v1.md §7.8/
RF-14/RF-25i (finestra_giorni_X, come cadenza_giorni_X) — richiesto
esplicitamente dall'utente durante l'implementazione del vincolo RF-25i
(finestra <= cadenza di generazione proposte). Il vecchio nome
("finestra_risposta_match_giorni", ordine delle parole diverso) era stato
scelto prima che questa convenzione fosse formalizzata nel documento.

Preserva valore/descrizione/data_ultima_modifica esistenti (UPDATE del
nome chiave, non DELETE+INSERT) — non è un nuovo parametro, è lo stesso
con un nome diverso.

Idempotente (no-op se la vecchia chiave non esiste più).

Uso:
    python scripts/migrate_2026_09_05_rinomina_finestra_risposta.py            (DB locale)
    python scripts/migrate_2026_09_05_rinomina_finestra_risposta.py --render   (DB Render)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

VECCHIA_CHIAVE = "finestra_risposta_match_giorni"
NUOVA_CHIAVE = "finestra_giorni_risposta_match"
NUOVA_DESCRIZIONE = (
    "RF-14/RF-25i: giorni entro cui entrambe le parti devono accettare la proposta prima "
    "che scada — deve restare <= cadenza_giorni_proposta_abbinamento"
)


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
    cur.execute("SELECT chiave, valore FROM system_config WHERE chiave = %s", (VECCHIA_CHIAVE,))
    vecchia = cur.fetchone()

    cur.execute("SELECT chiave, valore FROM system_config WHERE chiave = %s", (NUOVA_CHIAVE,))
    nuova_gia_presente = cur.fetchone()

    if nuova_gia_presente:
        print(f"'{NUOVA_CHIAVE}' già presente (valore={nuova_gia_presente['valore']}) — nessuna azione.")
        conn.close()
        return

    if not vecchia:
        print(f"'{VECCHIA_CHIAVE}' non trovata e '{NUOVA_CHIAVE}' non presente — inserisco il default (7).")
        cur.execute(
            "INSERT INTO system_config (chiave, valore, descrizione) VALUES (%s, '7', %s)",
            (NUOVA_CHIAVE, NUOVA_DESCRIZIONE),
        )
        conn.commit()
        print(f"'{NUOVA_CHIAVE}' inserita con default 7.")
        conn.close()
        return

    cur.execute(
        "UPDATE system_config SET chiave = %s, descrizione = %s WHERE chiave = %s",
        (NUOVA_CHIAVE, NUOVA_DESCRIZIONE, VECCHIA_CHIAVE),
    )
    conn.commit()
    print(f"Rinominata: '{VECCHIA_CHIAVE}' (valore={vecchia['valore']}) -> '{NUOVA_CHIAVE}'.")
    conn.close()


if __name__ == "__main__":
    main()
