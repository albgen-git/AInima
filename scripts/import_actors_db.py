"""
import_actors_db.py
Importa i 1000 profili del DB Actor (MySQL, esportato in
data_migration/Export ActorDB.csv) nello schema PostgreSQL di Ainima.

Popola: users, physical_profile, socio_profile.
Non tocca: dealbreaker_criteria, soft_criteria, psychometric_scores,
matches, match_feedback — il DB Actor non contiene questi dati
(v. avviso in CLAUDE.md), andranno generati sinteticamente in un
passaggio successivo.

Uso: python import_actors_db.py
"""

import csv
import os
import shutil
import uuid

import numpy as np
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTORS_DIR = os.path.join(BASE_DIR, "data_migration", "Actors DB", "Actors DB")
CSV_PATH = os.path.join(BASE_DIR, "data_migration", "Export ActorDB.csv")
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "photos")

load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# ── Mappature lookup (da db/schema.sql originale del DB Actor, MySQL) ─────────
GENERE = {1: "Maschile", 2: "Femminile", 3: "Non binario", 4: "Altro"}
ORIENTAMENTO = {
    1: "Eterosessuale", 2: "Omosessuale", 3: "Bisessuale",
    4: "Pansessuale", 5: "Asessuale", 6: "Altro",
}
CORPORATURA = {1: "Esile", 2: "Normale", 3: "Atletica", 4: "Robusta", 5: "Sovrappeso"}
COLORE_CAPELLI = {
    1: "Nero", 2: "Castano scuro", 3: "Castano chiaro", 4: "Biondo",
    5: "Rosso", 6: "Grigio", 7: "Bianco", 8: "Tinto/Colorato", 9: "Calvo",
}
COLORE_OCCHI = {1: "Marroni", 2: "Neri", 3: "Azzurri", 4: "Verdi", 5: "Grigi", 6: "Nocciola", 7: "Ambra"}
STILE_VITA = {
    1: "Sedentario", 2: "Moderatamente attivo", 3: "Attivo",
    4: "Molto attivo", 5: "Sportivo professionista",
}
TITOLO_STUDIO = {
    1: "Nessun titolo", 2: "Licenza elementare", 3: "Licenza media",
    4: "Diploma superiore", 5: "Laurea triennale", 6: "Laurea magistrale",
    7: "Dottorato di ricerca", 8: "Master",
}
SETTORE_OCCUPAZIONALE = {
    1: "Disoccupato", 2: "Studente", 3: "Pensionato", 4: "Arte e spettacolo",
    5: "Tecnologia e informatica", 6: "Sanità e medicina", 7: "Istruzione e ricerca",
    8: "Commercio e vendite", 9: "Finanza e banca", 10: "Edilizia e ingegneria",
    11: "Agricoltura", 12: "Trasporti e logistica", 13: "Pubblica amministrazione",
    14: "Ristorazione e turismo", 15: "Legge e giustizia", 16: "Sport e fitness",
    17: "Media e comunicazione", 18: "Artigianato",
}
FASCIA_REDDITO = {
    1: "Nessun reddito", 2: "< 15.000 €/anno", 3: "15.000 – 25.000 €/anno",
    4: "25.000 – 40.000 €/anno", 5: "40.000 – 60.000 €/anno",
    6: "60.000 – 100.000 €/anno", 7: "> 100.000 €/anno",
}
FEDE_RELIGIOSA = {
    1: "Nessuna", 2: "Cristiana cattolica", 3: "Cristiana protestante",
    4: "Cristiana ortodossa", 5: "Islamica", 6: "Ebraica", 7: "Buddista",
    8: "Induista", 9: "Agnostica", 10: "Atea", 11: "Altra",
}


def load_embeddings(cache_file, ids_file):
    vecs = np.load(cache_file)
    ids = np.load(ids_file).tolist()
    return {int(ids[i]): vecs[i].tolist() for i in range(len(ids))}


def main():
    pg_conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
    )
    pg_conn.autocommit = False
    cur = pg_conn.cursor()

    with open(os.path.join(BASE_DIR, "db", "schema.sql"), encoding="utf-8") as f:
        cur.execute(f.read())
    pg_conn.commit()
    print("Schema applicato.")

    profile_embs = load_embeddings(
        os.path.join(ACTORS_DIR, "embeddings_cache.npy"),
        os.path.join(ACTORS_DIR, "embeddings_ids.npy"),
    )
    pi_embs = load_embeddings(
        os.path.join(ACTORS_DIR, "pi_embeddings_cache.npy"),
        os.path.join(ACTORS_DIR, "pi_embeddings_ids.npy"),
    )
    print(f"Embedding caricati: {len(profile_embs)} profilo, {len(pi_embs)} partner ideale.")

    os.makedirs(os.path.join(STORAGE_DIR, "profilo"), exist_ok=True)
    os.makedirs(os.path.join(STORAGE_DIR, "partner_ideale"), exist_ok=True)

    inserted = 0
    skipped_photos = []

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            actor_id = int(row["id"])
            user_id = uuid.uuid4()

            genere = GENERE[int(row["id_genere"])]
            orientamento = ORIENTAMENTO[int(row["id_orientamento"])]

            # ── foto: copia in storage locale col nuovo user_id ────────────
            src_profilo = os.path.join(ACTORS_DIR, "images", f"{actor_id}.jpg")
            src_pi = os.path.join(ACTORS_DIR, "images_pi", f"{actor_id}.jpg")
            dst_profilo_rel = f"profilo/{user_id}.jpg"
            dst_pi_rel = f"partner_ideale/{user_id}.jpg"

            if os.path.exists(src_profilo):
                shutil.copyfile(src_profilo, os.path.join(STORAGE_DIR, dst_profilo_rel))
            else:
                dst_profilo_rel = None
                skipped_photos.append(("profilo", actor_id))

            if os.path.exists(src_pi):
                shutil.copyfile(src_pi, os.path.join(STORAGE_DIR, dst_pi_rel))
            else:
                dst_pi_rel = None
                skipped_photos.append(("partner_ideale", actor_id))

            # ── users ────────────────────────────────────────────────────
            # stato_account='Attivo': dato sintetico di test, bypassa volutamente
            # l'onboarding reale (RF-09) per popolare subito il pool di matching.
            cur.execute(
                """
                INSERT INTO users (
                    user_id, nome, cognome, data_nascita, genere,
                    orientamento_sessuale, stato_account, source_actor_id
                ) VALUES (%s, %s, %s, %s, %s, %s, 'Attivo', %s)
                """,
                (str(user_id), row["nome"], row["cognome"], row["data_di_nascita"],
                 genere, orientamento, actor_id),
            )

            # ── physical_profile ─────────────────────────────────────────
            emb_profilo = profile_embs.get(actor_id)
            emb_pi = pi_embs.get(actor_id)
            cur.execute(
                """
                INSERT INTO physical_profile (
                    user_id, altezza_cm, peso_kg, corporatura, colore_capelli,
                    colore_occhi, fumo, alcol, foto_profilo_url,
                    foto_partner_ideale_url, embedding_visivo_profilo,
                    embedding_visivo_partner_ideale
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(user_id), int(row["altezza_cm"]), float(row["peso_kg"]),
                    CORPORATURA[int(row["id_corporatura"])],
                    COLORE_CAPELLI[int(row["id_colore_capelli"])],
                    COLORE_OCCHI[int(row["id_colore_occhi"])],
                    row["fumo"] == "1", row["alcool"] == "1",
                    dst_profilo_rel, dst_pi_rel, emb_profilo, emb_pi,
                ),
            )

            # ── socio_profile ────────────────────────────────────────────
            # comune_residenza/coordinate_gps: NULL, non presenti nel DB Actor
            # (che ha solo luogo_nascita, semanticamente diverso) — v. CLAUDE.md.
            cur.execute(
                """
                INSERT INTO socio_profile (
                    user_id, titolo_studio, settore_occupazionale,
                    fascia_reddito, fede_religiosa, importanza_religione
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(user_id),
                    TITOLO_STUDIO[int(row["id_titolo_studio"])],
                    SETTORE_OCCUPAZIONALE[int(row["id_settore_occupazionale"])],
                    FASCIA_REDDITO[int(row["id_fascia_reddito"])],
                    FEDE_RELIGIOSA[int(row["id_fede_religiosa"])],
                    int(row["importanza_religione"]),
                ),
            )

            inserted += 1

    pg_conn.commit()
    print(f"Importati {inserted} utenti.")
    if skipped_photos:
        print(f"Foto mancanti (loggate, non bloccanti): {len(skipped_photos)}")
        for kind, aid in skipped_photos[:20]:
            print(f"  [{kind}] actor_id={aid}")

    cur.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
