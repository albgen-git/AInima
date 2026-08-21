"""Liste "Mi Piace/Non Sopporto" e "Partner Vorrei/Non Vorrei" (RF-08c,
v. docs/Ainima_Liste_Piace_Detesta_v1.md) — testo libero corto (non
narrativa), parsing deterministico + embedding per singolo tag con cache
CONDIVISA tra tutti gli utenti (tag_embedding_cache): un tag mai visto
viene incorporato una sola volta, poi riusato — i tag comuni si esauriscono
presto. Zero LLM in questo modulo, solo un modello di embedding (stesso
principio delle foto/embedding testuale narrativo) + confronto matematico."""

import re

import numpy as np

from services import text_embedding

# Pulizia minima (doc §8): niente URL o numeri lunghi che potrebbero
# inquinare silenziosamente la cache condivisa usata da tutti gli utenti.
_NON_PERTINENTE = re.compile(r"https?://\S+|\d{4,}")


def normalizza_tag(testo_grezzo: str | None) -> list[str]:
    """Step 1 (doc §2): split su virgola, trim, lowercase, dedup."""
    if not testo_grezzo:
        return []
    grezzi = [t.strip().lower() for t in testo_grezzo.split(",")]
    puliti = []
    visti = set()
    for t in grezzi:
        if not t or _NON_PERTINENTE.search(t):
            continue
        if t not in visti:
            visti.add(t)
            puliti.append(t)
    return puliti


def get_or_compute_embeddings(tags: list[str], cur) -> dict[str, list[float]]:
    """Step 2 (doc §2): legge dalla cache condivisa i tag già visti,
    calcola l'embedding solo per quelli nuovi e li salva per il futuro."""
    if not tags:
        return {}
    cur.execute(
        "SELECT tag_normalizzato, embedding_vector FROM tag_embedding_cache WHERE tag_normalizzato = ANY(%s)",
        (tags,),
    )
    trovati = {r["tag_normalizzato"]: r["embedding_vector"] for r in cur.fetchall()}
    for tag in tags:
        if tag in trovati:
            continue
        embedding = text_embedding.embed_testo(tag)
        cur.execute(
            """INSERT INTO tag_embedding_cache (tag_normalizzato, embedding_vector, modello_embedding)
               VALUES (%s, %s, %s) ON CONFLICT (tag_normalizzato) DO NOTHING""",
            (tag, embedding, text_embedding.MODELLO_EMBEDDING),
        )
        trovati[tag] = embedding
    return trovati


def get_centroide(cur) -> list[float] | None:
    """Correzione anisotropia (v. CLAUDE.md 2026-08-20): gemini-embedding-001
    su testo cortissimo ha una similarità coseno di base anomala anche fra
    tag scollegati (verificato empiricamente, ~0.6 anche fra non-parole
    senza significato) — un problema geometrico dello spazio vettoriale, non
    semantico. Sottrarre questo centroide prima del confronto separa
    nettamente meglio tag simili da tag scollegati.

    None se non ancora calcolato (cache vuota alla prima esecuzione) — in
    quel caso i chiamanti devono degradare a nessuna correzione, non
    fallire: un tag_overlap_score senza centraggio resta comunque valido,
    solo meno discriminante."""
    cur.execute("SELECT vettore FROM tag_embedding_centroide WHERE id = 1")
    riga = cur.fetchone()
    return riga["vettore"] if riga else None


def ricalcola_centroide(cur) -> dict | None:
    """Ricalcola il centroide sulla cache tag CONDIVISA (tutti i tag mai
    visti da nessun utente, non solo quelli del pool corrente) e lo
    persiste. Nessuno scheduler reale: va rilanciato manualmente (script
    dedicato) man mano che la cache cresce — stesso limite già accettato
    altrove nel progetto per l'assenza di un vero cron (v. CLAUDE.md).

    Se la cache contiene vettori prodotti da modelli di embedding diversi
    (es. Google ha silenziosamente cambiato il comportamento del modello,
    v. modello_embedding in db/schema.sql), il centroide li mischierebbe
    senza che nessuno se ne accorga — qui si limita a segnalarlo (stampa),
    non blocca il calcolo: decidere se/come ricalcolare i tag vecchi resta
    una scelta manuale."""
    cur.execute("SELECT embedding_vector, modello_embedding FROM tag_embedding_cache")
    righe = cur.fetchall()
    if not righe:
        return None

    modelli = {r["modello_embedding"] for r in righe}
    if len(modelli) > 1:
        print(f"[ATTENZIONE] tag_embedding_cache contiene vettori da {len(modelli)} modelli diversi: {modelli} — il centroide li sta mescolando.")

    vettori = np.array([r["embedding_vector"] for r in righe])
    centroide = vettori.mean(axis=0).tolist()
    cur.execute("""
        INSERT INTO tag_embedding_centroide (id, vettore, numero_tag_campione, calcolato_il)
        VALUES (1, %s, %s, now())
        ON CONFLICT (id) DO UPDATE SET
            vettore = EXCLUDED.vettore, numero_tag_campione = EXCLUDED.numero_tag_campione,
            calcolato_il = EXCLUDED.calcolato_il
    """, (centroide, len(righe)))
    return {"vettore": centroide, "numero_tag_campione": len(righe), "modelli": modelli}
