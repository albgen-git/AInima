"""Torneo estetico — Parte 1 (MVP): popola torneo_estetico_cluster con 8
rappresentanti per genere (Maschile/Femminile), estratti CASUALMENTE dal
pool demo con foto profilo valida — non un vero clustering a embedding
(v. CLAUDE.md 2026-09-06, decisione esplicita dell'utente: "in questa fase
vorrei meno chiamate API... il vero potenziale sarà disponibile in
produzione, quando avremo il vero DB"). Zero chiamate AWS.

Script offline, una tantum sul pool di test attuale — non per utente.
Quando in produzione si userà un set fotografico nuovo (o un vero
clustering a embedding), questo script va rieseguito da capo: nessuna
migrazione prevista, il DB di test si abbandona (non si converte).

Idempotente per rilancio pulito: cancella tutte le righe torneo_estetico_
cluster esistenti prima di ripopolare, per non accumulare set multipli
tra un rilancio e l'altro durante lo sviluppo.

Uso:
    python scripts/genera_cluster_torneo_estetico.py            (DB locale)
    python scripts/genera_cluster_torneo_estetico.py --render   (DB Render)
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

N_PER_GENERE = 8
GENERI = ["Maschile", "Femminile"]


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

    cur.execute("DELETE FROM torneo_estetico_confronti")
    cur.execute("DELETE FROM preferenza_estetica_utente")
    cur.execute("DELETE FROM torneo_estetico_cluster")
    conn.commit()
    print("Tabelle torneo estetico ripulite prima del ripopolamento.")

    rng = random.Random(2026_09_06)  # seed fisso: rilanci ripetibili durante lo sviluppo

    for genere in GENERI:
        cur.execute("""
            SELECT u.user_id, u.source_actor_id, p.foto_profilo_url
            FROM users u JOIN physical_profile p ON p.user_id = u.user_id
            WHERE u.is_demo = TRUE AND u.genere = %s AND p.foto_profilo_url IS NOT NULL
        """, (genere,))
        pool = cur.fetchall()
        print(f"{genere}: pool di {len(pool)} foto valide")

        scelti = rng.sample(pool, N_PER_GENERE)
        for r in scelti:
            cur.execute("""
                INSERT INTO torneo_estetico_cluster (genere, foto_url, source_actor_id, metodo_selezione)
                VALUES (%s, %s, %s, 'casuale_mvp')
            """, (genere, r["foto_profilo_url"], r["source_actor_id"]))
        conn.commit()
        print(f"{genere}: {N_PER_GENERE} rappresentanti inseriti.")

    cur.execute("SELECT genere, cluster_id, source_actor_id, foto_url FROM torneo_estetico_cluster ORDER BY genere, cluster_id")
    print()
    print("Rappresentanti finali:")
    for r in cur.fetchall():
        print(" ", dict(r))

    conn.close()


if __name__ == "__main__":
    main()
