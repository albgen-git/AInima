"""Backfill lingue_parlate + redistribuzione geografica sul pool demo
(1000 profili, source_actor_id IS NOT NULL) — v. CLAUDE.md.

Motivazione: un tentativo di abbinamento per Danae Almeida (utente reale,
sede Dubai) ha dato "nessun_candidato" — causa isolata: valuta_distanza()
richiede una lingua condivisa oltre soglia_area_urbana_km (50km), ma
TUTTI i 1000 profili demo avevano lingue_parlate NULL (gap già segnalato
in CLAUDE.md il 17/08, mai risolto) — un blocco strutturale contro
l'intero pool, non un problema del profilo di Danae.

Nota su "preferenza lingua partner" (chiesta esplicitamente dall'utente,
con dubbio): NON esiste un campo dedicato nello schema — l'algoritmo usa
solo l'intersezione di lingue_parlate tra i due lati (self, non una
preferenza dichiarata separata, v. Ainima_Algoritmo_Ranking_Finale_v1.md
§3bis). Ampliare la copertura linguistica del pool è già sufficiente per
l'obiettivo "preferenze larghe" — non serve alcun nuovo campo.

Redistribuzione geografica (richiesta esplicita): 800 profili restano in
Italia (invariati, nessun cambio di città/coordinate), 150 spostati tra
Dubai/Abu Dhabi, 50 sparpagliati in una selezione di capitali mondiali.
Aggiornati anche `users.mercato`/`valuta` per i 200 spostati — nessun
codice li legge per logica di business (verificato: solo
admin_viewer.py li mostra come campi editabili), quindi un cambio è
puramente informativo, coerente con lo scopo dichiarato di questi 2
campi fin dalla decisione Dubai del 12/08 (v. CLAUDE.md).

Split gruppo→sottogruppo dettagliato in RIPARTIZIONE sotto, deterministico
via un singolo shuffle a seed fisso sull'elenco ordinato per
source_actor_id (garantisce i conteggi esatti 800/150/50 e rende lo
script idempotente: stesso input -> stesso risultato ad ogni rilancio).
Le scelte per-utente (quali lingue, quale città tra le capitali) usano
invece un RNG seedato per singolo utente (source_actor_id * 7919 + 41,
offset distinto da tutti gli altri generatori di questo progetto).

Deliberatamente NON propagato tramite scripts/seed_render_from_local.py
(che tocca anche matches/foto/altre tabelle, un'operazione molto più
pesante di quanto serva qui) — essendo interamente deterministico
(RNG seedato su source_actor_id, nessuna dipendenza da uno stato letto
da un'altra fonte), va invece rilanciato identico su ciascun DB con
--render, stesso pattern già in uso per le migrazioni di questo progetto.

Uso:
    python scripts/backfill_lingue_localizzazione_pool.py                     (locale, dry-run)
    python scripts/backfill_lingue_localizzazione_pool.py --live               (locale, scrive davvero)
    python scripts/backfill_lingue_localizzazione_pool.py --render --live      (Render, scrive davvero)
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn  # noqa: E402

SEED_SPLIT_GRUPPI = 20260905  # shuffle unico per i conteggi esatti 800/150/50
OFFSET_PER_UTENTE = 41

N_ITALIA = 800
N_DUBAI_ABU_DHABI = 150
N_CAPITALI = 50

DUBAI_ABU_DHABI = [
    ("Dubai", 55.2708, 25.2048),
    ("Abu Dhabi", 54.3773, 24.4539),
]

# (città, lon, lat, lingua locale, valuta) — selezione diversificata per
# continente, "sparpagliati per il mondo, nelle capitali" come richiesto.
CAPITALI_MONDO = [
    ("Parigi", 2.3522, 48.8566, "Francese", "EUR"),
    ("Londra", -0.1278, 51.5074, "Inglese", "GBP"),
    ("Madrid", -3.7038, 40.4168, "Spagnolo", "EUR"),
    ("Berlino", 13.4050, 52.5200, "Tedesco", "EUR"),
    ("Lisbona", -9.1393, 38.7223, "Portoghese", "EUR"),
    ("Vienna", 16.3738, 48.2082, "Tedesco", "EUR"),
    ("Atene", 23.7275, 37.9838, "Greco", "EUR"),
    ("Varsavia", 21.0122, 52.2297, "Polacco", "PLN"),
    ("Il Cairo", 31.2357, 30.0444, "Arabo", "EGP"),
    ("Washington", -77.0369, 38.9072, "Inglese", "USD"),
    ("Ottawa", -75.6972, 45.4215, "Inglese", "CAD"),
    ("Città del Messico", -99.1332, 19.4326, "Spagnolo", "MXN"),
    ("Buenos Aires", -58.3816, -34.6037, "Spagnolo", "ARS"),
    ("Brasilia", -47.8825, -15.7942, "Portoghese", "BRL"),
    ("Tokyo", 139.6917, 35.6895, "Giapponese", "JPY"),
    ("Singapore", 103.8198, 1.3521, "Inglese", "SGD"),
    ("Canberra", 149.1300, -35.2809, "Inglese", "AUD"),
    ("Nairobi", 36.8219, -1.2921, "Inglese", "KES"),
]


def _lingue_italia(rng: random.Random) -> list[str]:
    r = rng.random()
    if r < 0.70:
        return ["Italiano"]
    if r < 0.90:
        return ["Italiano", "Inglese"]
    terza = rng.choice(["Francese", "Spagnolo", "Tedesco"])
    return ["Italiano", "Inglese", terza]


def _lingue_dubai(rng: random.Random) -> list[str]:
    # ~50% include Italiano (comunità/diaspora italiana — risolve
    # direttamente il caso Danae) — l'altra metà resta comunque
    # ampiamente compatibile via Inglese, la lingua franca dell'area.
    if rng.random() < 0.5:
        return rng.choice([
            ["Italiano", "Inglese"],
            ["Italiano", "Inglese", "Arabo"],
        ])
    return rng.choice([
        ["Inglese", "Arabo"],
        ["Inglese"],
        ["Inglese", "Francese"],
    ])


def _lingue_capitale(rng: random.Random, lingua_locale: str) -> list[str]:
    lingue = [lingua_locale]
    if lingua_locale != "Inglese" and rng.random() < 0.6:
        lingue.append("Inglese")
    if rng.random() < 0.2 and "Italiano" not in lingue:
        lingue.append("Italiano")
    return lingue


def _connetti(usa_render: bool):
    if usa_render:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    return get_conn()


def main():
    live = "--live" in sys.argv
    usa_render = "--render" in sys.argv
    conn = _connetti(usa_render)
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.source_actor_id FROM users u
        WHERE u.is_demo = TRUE ORDER BY u.source_actor_id
    """)
    utenti = cur.fetchall()
    assert len(utenti) == 1000, f"attesi 1000 profili demo, trovati {len(utenti)}"

    ids = list(utenti)
    random.Random(SEED_SPLIT_GRUPPI).shuffle(ids)
    gruppo_italia = ids[:N_ITALIA]
    gruppo_dubai = ids[N_ITALIA:N_ITALIA + N_DUBAI_ABU_DHABI]
    gruppo_capitali = ids[N_ITALIA + N_DUBAI_ABU_DHABI:]
    assert len(gruppo_capitali) == N_CAPITALI

    print(f"Piano: Italia={len(gruppo_italia)}, Dubai/Abu Dhabi={len(gruppo_dubai)}, Capitali={len(gruppo_capitali)}")

    aggiornati = 0

    # ── Italia: SOLO lingue_parlate + importanza (nessun cambio città) ──
    for u in gruppo_italia:
        rng = random.Random(u["source_actor_id"] * 7919 + OFFSET_PER_UTENTE)
        lingue = _lingue_italia(rng)
        importanza = round(rng.uniform(0.1, 0.5), 2)
        if live:
            cur.execute(
                "UPDATE socio_profile SET lingue_parlate = %s, importanza_vicinanza_geografica = %s WHERE user_id = %s",
                (lingue, importanza, str(u["user_id"])),
            )
        aggiornati += 1

    # ── Dubai / Abu Dhabi ──
    for i, u in enumerate(gruppo_dubai):
        rng = random.Random(u["source_actor_id"] * 7919 + OFFSET_PER_UTENTE)
        citta, lon, lat = DUBAI_ABU_DHABI[0] if i < 100 else DUBAI_ABU_DHABI[1]
        lingue = _lingue_dubai(rng)
        importanza = round(rng.uniform(0.05, 0.3), 2)
        if live:
            cur.execute("""
                UPDATE socio_profile SET comune_residenza = %s, coordinate_gps = point(%s, %s),
                       lingue_parlate = %s, importanza_vicinanza_geografica = %s
                WHERE user_id = %s
            """, (citta, lon, lat, lingue, importanza, str(u["user_id"])))
            cur.execute("UPDATE users SET mercato = %s, valuta = 'AED' WHERE user_id = %s",
                        (citta, str(u["user_id"])))
        aggiornati += 1

    # ── Capitali del mondo, sparpagliate (round-robin sulla lista) ──
    for i, u in enumerate(gruppo_capitali):
        rng = random.Random(u["source_actor_id"] * 7919 + OFFSET_PER_UTENTE)
        citta, lon, lat, lingua_locale, valuta = CAPITALI_MONDO[i % len(CAPITALI_MONDO)]
        lingue = _lingue_capitale(rng, lingua_locale)
        importanza = round(rng.uniform(0.05, 0.3), 2)
        if live:
            cur.execute("""
                UPDATE socio_profile SET comune_residenza = %s, coordinate_gps = point(%s, %s),
                       lingue_parlate = %s, importanza_vicinanza_geografica = %s
                WHERE user_id = %s
            """, (citta, lon, lat, lingue, importanza, str(u["user_id"])))
            cur.execute("UPDATE users SET mercato = %s, valuta = %s WHERE user_id = %s",
                        (citta, valuta, str(u["user_id"])))
        aggiornati += 1

    if live:
        conn.commit()
        print(f"Applicato dal vivo: {aggiornati} profili aggiornati.")
    else:
        print(f"DRY-RUN: {aggiornati} profili sarebbero aggiornati (nessuna scrittura). Rilancia con --live per applicare.")
        conn.rollback()

    conn.close()


if __name__ == "__main__":
    main()
