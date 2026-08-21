"""
generate_interest_tags_data.py
Genera le 4 liste libere RF-08c (interest_tags.mi_piace/non_sopporto/
partner_vorrei/partner_non_vorrei) per i 1000 profili di test — servono a
poter misurare Punteggio_Tag_Liste (STEP 4) su scala reale, non solo sui
pochi utenti verificati a mano durante lo sviluppo (v. CLAUDE.md 2026-08-20).

Testo generato per COMBINAZIONE di tag pescati (RNG seedato su
source_actor_id, riproducibile — stesso pattern di generate_synthetic_data.py
e generate_narrative_data.py, offset diverso per non correlare con
nessuno dei due) da banchi tematici CONDIVISI con generate_narrative_data.py
(stessi VOCABOLARIO_INTERESSI/VOCABOLARIO_FASTIDI del pattern "amo/odio" già
lì) — stesso universo di concetti fra i campi liberi narrativi e le liste
strutturate di uno stesso profilo, non due generatori scollegati.

Coerenza interna per costruzione (non solo esterna con la narrativa):
- mi_piace/partner_vorrei pescano da un vocabolario di interessi, mai
  contraddetti dal proprio non_sopporto/partner_non_vorrei (vocabolario
  disgiunto: interessi vs. difetti/fastidi, domini diversi per costruzione).
- Se il profilo ha già stile_vita_sport (physical_profile) valorizzato, lo
  si include sempre in mi_piace — non è un tag inventato, è già un dato
  reale della persona.
- Il numero di interessi dichiarati varia con l'apertura Big Five (più alta
  apertura -> più interessi elencati) invece di essere fisso per tutti.

Dopo aver scritto le liste, calcola/riusa (stessa funzione dell'endpoint
reale, tag_matching.get_or_compute_embeddings) l'embedding di ogni tag
tramite la cache condivisa, poi ricalcola il centroide di correzione
anisotropia su un campione molto più rappresentativo (v. CLAUDE.md) di
quello disponibile finora (13 tag da soli test manuali).

Uso: python scripts/generate_interest_tags_data.py
"""

import os
import random
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from db import get_conn  # noqa: E402
from services import tag_matching  # noqa: E402

# ── Vocabolari — stesso universo tematico di generate_narrative_data.py
# (TEMI_AMBIVALENTI/PARTNER_ATTIVITA/PARTNER_DIFETTI/TEMI_SOLO_NEGATIVI),
# qui come tag brevi invece che frasi intere, più qualità caratteriali per
# partner_vorrei (assenti nel generatore narrativo, servono qui perché
# "vorrei" può esprimere anche una qualità, non solo un interesse condiviso).
VOCABOLARIO_INTERESSI = [
    "gatti", "cani", "biliardo", "viaggiare", "cucinare", "il mare", "la montagna",
    "leggere", "ballare", "correre", "concerti dal vivo", "scacchi", "buon vino",
    "mercatini dell'usato", "fotografia", "andare in bici", "trekking", "musei",
    "pizza", "tramonti", "palestra", "film horror", "reality show", "karaoke",
    "cruciverba", "cinema", "cucina piccante", "giochi da tavolo", "giardinaggio",
    "serie tv", "buon caffè", "arte", "sport all'aperto", "musica dal vivo",
    "i boschi", "gli animali", "scoprire posti nuovi",
]

VOCABOLARIO_FASTIDI = [
    "le persone false", "la maleducazione", "chi non mantiene la parola data",
    "l'arroganza", "la gelosia eccessiva", "le bugie", "chi giudica senza conoscere",
    "la superficialità", "l'egoismo", "chi non ha rispetto per gli altri",
    "chi non si assume le proprie responsabilità", "la scortesia gratuita",
    "le file lunghe", "la mancanza di puntualità", "il rumore del traffico",
    "il caldo estremo", "i mezzi pubblici affollati", "chi non risponde ai messaggi",
    "il freddo pungente", "chi parla ad alta voce al telefono", "la pigrizia",
]

VOCABOLARIO_QUALITA_PARTNER = [
    "ironia", "curiosità", "gentilezza", "affidabilità", "sincerità", "empatia",
    "ambizione", "dolcezza", "intelligenza", "generosità", "pazienza",
    "spontaneità", "sensibilità", "determinazione", "creatività",
    "senso dell'umorismo",
]


def genera_liste(rng, dati):
    apertura = dati["apertura"] if dati["apertura"] is not None else 0.5
    n_piace = rng.randint(3, 5) if apertura > 0.6 else rng.randint(2, 3)

    interessi = rng.sample(VOCABOLARIO_INTERESSI, n_piace)
    sport = (dati["stile_vita_sport"] or "").strip().lower()
    if sport and sport not in interessi:
        interessi[rng.randrange(len(interessi))] = sport
    mi_piace = ", ".join(interessi)

    non_sopporto = ", ".join(rng.sample(VOCABOLARIO_FASTIDI, rng.randint(1, 3)))

    vorrei_interessi = rng.sample(VOCABOLARIO_INTERESSI, rng.randint(1, 2))
    vorrei_qualita = rng.sample(VOCABOLARIO_QUALITA_PARTNER, rng.randint(1, 2))
    partner_vorrei = ", ".join(vorrei_interessi + vorrei_qualita)

    partner_non_vorrei = ", ".join(rng.sample(VOCABOLARIO_FASTIDI, rng.randint(1, 2)))

    return mi_piace, non_sopporto, partner_vorrei, partner_non_vorrei


def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.source_actor_id, p.stile_vita_sport,
               ps.score_big5_apertura AS apertura
        FROM users u
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        WHERE u.source_actor_id IS NOT NULL
        ORDER BY u.source_actor_id
    """)
    rows = cur.fetchall()
    print(f"Profili da completare: {len(rows)}")

    n_scritti = 0
    tutti_i_tag_visti = set()
    for r in rows:
        seed = r["source_actor_id"] * 7919 + 11  # offset diverso dagli altri due generatori
        rng = random.Random(seed)

        mi_piace, non_sopporto, partner_vorrei, partner_non_vorrei = genera_liste(rng, r)

        mi_piace_tags = tag_matching.normalizza_tag(mi_piace)
        non_sopporto_tags = tag_matching.normalizza_tag(non_sopporto)
        partner_vorrei_tags = tag_matching.normalizza_tag(partner_vorrei)
        partner_non_vorrei_tags = tag_matching.normalizza_tag(partner_non_vorrei)
        tutti_i_tag_visti.update(mi_piace_tags + non_sopporto_tags + partner_vorrei_tags + partner_non_vorrei_tags)

        cur.execute("""
            INSERT INTO interest_tags (
                user_id, mi_piace, non_sopporto, partner_vorrei, partner_non_vorrei,
                mi_piace_tags, non_sopporto_tags, partner_vorrei_tags, partner_non_vorrei_tags,
                data_ultima_modifica
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                mi_piace = EXCLUDED.mi_piace, non_sopporto = EXCLUDED.non_sopporto,
                partner_vorrei = EXCLUDED.partner_vorrei, partner_non_vorrei = EXCLUDED.partner_non_vorrei,
                mi_piace_tags = EXCLUDED.mi_piace_tags, non_sopporto_tags = EXCLUDED.non_sopporto_tags,
                partner_vorrei_tags = EXCLUDED.partner_vorrei_tags,
                partner_non_vorrei_tags = EXCLUDED.partner_non_vorrei_tags,
                data_ultima_modifica = now()
        """, (str(r["user_id"]), mi_piace, non_sopporto, partner_vorrei, partner_non_vorrei,
              mi_piace_tags, non_sopporto_tags, partner_vorrei_tags, partner_non_vorrei_tags))
        n_scritti += 1

    conn.commit()
    print(f"Completato: {n_scritti} profili aggiornati.")

    print(f"Calcolo/riuso embedding per {len(tutti_i_tag_visti)} tag unici (cache condivisa)...")
    tag_matching.get_or_compute_embeddings(list(tutti_i_tag_visti), cur)
    conn.commit()

    print("Ricalcolo il centroide anisotropia sul campione ora molto più ampio...")
    esito = tag_matching.ricalcola_centroide(cur)
    conn.commit()
    if esito:
        print(f"Centroide ricalcolato su {esito['numero_tag_campione']} tag.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
