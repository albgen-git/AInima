"""Migrazione live: inserisce la riga stable_v9 in matching_algorithm_versions
(v. CLAUDE.md — migrazione AWS Rekognition). Gap reale: matching_engine.
ALGORITMO_VERSIONE era già stato bumpato a "stable_v9" nel codice senza la
riga corrispondente in questa tabella — un vero INSERT su matches con questa
versione avrebbe violato la FK. Nessun match reale è mai stato creato con
questa versione nel frattempo (verificato), quindi la riga descrive lo stato
finale (bidirezionale + media geometrica) in un unico blocco.

Idempotente (ON CONFLICT DO NOTHING, sicuro da rilanciare).

Uso:
    python scripts/migrate_2026_09_03_stable_v9_versione.py            (DB locale, da .env PG*)
    python scripts/migrate_2026_09_03_stable_v9_versione.py --render   (DB Render, da .env DATABASE_URL)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DESCRIZIONE = (
    'Migrazione RF-08c/RF-11b da ArcFace/embedding precalcolato ad AWS Rekognition (v. CLAUDE.md): '
    'DetectFaces valida il volto all\'upload (soglia 90%), CompareFaces confronta on-demand la foto '
    '"partner ideale" del cercatore con la foto profilo di ogni candidato in shortlist al momento della '
    'proposta — nulla di precalcolato/persistito, embedding_visivo_profilo/embedding_visivo_partner_ideale '
    'rimossi da physical_profile. Selezione visiva BIDIREZIONALE (entrambe le direzioni, non solo '
    'cercatore->candidato — intento di prodotto: l\'abbinamento premia la coppia in cui ENTRAMBE le persone '
    'somigliano all\'ideale dichiarato dall\'altra), aggregata a MEDIA GEOMETRICA (non aritmetica) quando '
    'entrambe le direzioni sono calcolabili — la media aritmetica lasciava passare coppie con una direzione '
    'fortemente asimmetrica (es. 82/0.2 -> media 41), la geometrica collassa verso 0 in quel caso. Nessuna '
    'soglia minima di similarità (a differenza della calibrazione a percentile di stable_v5, pensata per un '
    'problema specifico di ArcFace che non si applica a un punteggio di confidenza "stessa persona" nativo '
    'come CompareFaces).'
)

SQL = """
INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v9', %s)
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
    cur.execute(SQL, (DESCRIZIONE,))
    conn.commit()
    print("matching_algorithm_versions: riga stable_v9 inserita (o già presente).")
    conn.close()


if __name__ == "__main__":
    main()
