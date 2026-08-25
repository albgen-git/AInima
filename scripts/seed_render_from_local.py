"""
seed_render_from_local.py
Seed/migrazione one-shot dal Postgres LOCALE (ainima — pool demo da ~1000
profili sintetici, già nello schema attuale, generato e verificato in
sessioni precedenti) al Postgres di COLLAUDO su Render, con le foto
ricaricate su Cloudflare R2 (S3-compatibile via boto3).

Fonte dati: il Postgres locale, NON il CSV/DB Actor grezzo
(data_migration/Export ActorDB.csv) — quel CSV contiene solo anagrafica/
fisico/socio-economico, mai criteri di ricerca né punteggi psicometrici
(v. scripts/import_actors_db.py, che lo importò a suo tempo). Il Postgres
locale ha già tutto, nello schema corrente — è la sorgente giusta per un
pool demo "subito visibile nel matching".

Il DB di collaudo su Render viene azzerato da Render ogni mese: lo script
è pensato per essere rilanciato da zero ad ogni ripristino (schema.sql
applicato di nuovo, idempotente) o per un aggiornamento incrementale
sicuro (upsert per user_id, mai duplica).

Fasi (in ordine):
  0. CREATE EXTENSION IF NOT EXISTS vector — richiesto esplicitamente,
     ma lo schema attuale NON usa ancora il tipo vector da nessuna parte
     (tutti gli embedding restano DOUBLE PRECISION[], v. CLAUDE.md) — un
     lavoro successivo dedicato, non toccato qui.
  1. Applica db/schema.sql (crea tabelle + i seed propri dello schema:
     system_config, matching_algorithm_versions).
  2. Copia tag_embedding_cache + tag_embedding_centroide (dato di
     riferimento condiviso, non per-utente — senza, il matching a tag
     "Mi piace/Non sopporto" del pool migrato non troverebbe alcun
     embedding e degraderebbe silenziosamente).
  3. Per ogni utente demo locale (source_actor_id IS NOT NULL):
     foto caricate su R2, poi le 8 righe satellite (physical_profile,
     socio_profile, dealbreaker_criteria, soft_criteria,
     psychometric_scores, interest_tags, profile_narrative) copiate
     upsert su Render con gli URL R2 al posto dei percorsi locali.
  4. matches + match_feedback (RF-22b, popola la Rubrica in demo senza
     un ciclo di matching live). Verificato sui dati reali prima di
     scrivere questo passo: i 387 match locali condividono TUTTI lo
     stesso identico istante (2026-08-13, un'unica generazione batch),
     con finestra_risposta_match_giorni=7 — 386/387 "Proposto" hanno
     quindi data_scadenza_risposta già scaduta rispetto a oggi. Le date
     (data_proposta/data_scadenza_risposta/data_conferma) vengono
     "ribasate" con un offset costante uguale per tutte le righe (la
     più recente diventa "ieri", finestra di risposta ancora aperta per
     chi è 'Proposto') — solo uno spostamento nel tempo, mai un cambio
     di stato/punteggio/coppia rispetto ai dati reali.

Uso:
    python scripts/seed_render_from_local.py [--dry-run] [--reset] [--limit N]

    --dry-run   non scrive né su R2 né su Render, stampa solo cosa
                verrebbe fatto (inclusi gli URL R2 che verrebbero generati)
    --reset     cancella prima (in ordine sicuro rispetto alle FK) tutte le
                righe del pool demo già presenti su Render, poi reinserisce
                da zero — utile dopo un azzeramento parziale/sporco
    --limit N   processa solo i primi N utenti demo (per una verifica
                rapida prima del run completo su ~1000 profili/~1780 foto)

Variabili d'ambiente richieste, oltre a quelle locali già in uso
(PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE, invariate — sono la SORGENTE):
    DATABASE_URL          connection string Postgres del DB di collaudo Render (TARGET)
    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_ENDPOINT_URL        endpoint API S3-compatibile per l'upload (boto3)
    R2_BUCKET_NAME
    R2_PUBLIC_BASE_URL     dominio pubblico da cui le foto sono servite —
                           NON è lo stesso di R2_ENDPOINT_URL (quello è
                           l'endpoint API per scrivere, questo è il dominio
                           di lettura pubblica) — mancava nell'elenco
                           originale, serve per costruire l'URL da salvare
                           in DB (es. il tuo dominio custom collegato al
                           bucket, o https://pub-<hash>.r2.dev)
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import boto3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import get_conn as connetti_locale  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "photos")
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# (tabella, colonna_chiave) — tutte le tabelle satellite del profilo demo,
# tutte PK su user_id, in un ordine che rispetta le FK per il --reset
# (cancellazione in ordine INVERSO a questa lista).
TABELLE_PROFILO_DEMO = [
    ("physical_profile", "user_id"),
    ("socio_profile", "user_id"),
    ("dealbreaker_criteria", "user_id"),
    ("soft_criteria", "user_id"),
    ("psychometric_scores", "user_id"),
    ("interest_tags", "user_id"),
    ("profile_narrative", "user_id"),
]


def connetti_render():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def url_pubblico(chiave_oggetto: str) -> str:
    base = os.environ.get("R2_PUBLIC_BASE_URL", "<R2_PUBLIC_BASE_URL non impostata>").rstrip("/")
    return f"{base}/{chiave_oggetto}"


def carica_foto_su_r2(client, path_locale: str, chiave_oggetto: str, dry_run: bool) -> str | None:
    """Ritorna l'URL pubblico se l'upload riesce (o in dry-run), None se
    fallisce — un fallimento di upload non deve far crashare l'intero
    run, solo lasciare quella singola foto senza URL (stesso principio
    già usato per l'invio email a lotti, v. CLAUDE.md: un fallimento
    isolato non deve corrompere il resto)."""
    if dry_run:
        return url_pubblico(chiave_oggetto)
    try:
        with open(path_locale, "rb") as f:
            client.put_object(
                Bucket=os.environ["R2_BUCKET_NAME"], Key=chiave_oggetto, Body=f,
                ContentType="image/jpeg",
            )
        return url_pubblico(chiave_oggetto)
    except Exception as e:
        print(f"  [ERRORE upload R2] {chiave_oggetto}: {e}")
        return None


def abilita_pgvector(cur, dry_run: bool):
    """Passo 0, richiesto esplicitamente. Lo schema attuale non usa
    ancora il tipo vector da nessuna parte (v. docstring del file) —
    l'estensione resta attiva ma inutilizzata finché non si fa la
    migrazione dedicata delle colonne embedding."""
    if dry_run:
        print("[dry-run] CREATE EXTENSION IF NOT EXISTS vector;")
        return
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("pgvector: estensione abilitata (o già presente).")
    except psycopg2.errors.InsufficientPrivilege as e:
        cur.connection.rollback()
        print("ERRORE: privilegi insufficienti per CREATE EXTENSION vector su questo DB.")
        print(f"Dettaglio esatto: {e}")
        print("Va abilitata manualmente da un utente con privilegi superiori "
              "(su Render: dashboard del database di collaudo, non del web service).")
        sys.exit(1)


def applica_schema(cur, dry_run: bool):
    """Passo 1 — idempotente: CREATE TABLE IF NOT EXISTS ovunque, i tipi
    enum sono creati dentro blocchi DO $$ ... EXCEPTION WHEN
    duplicate_object THEN NULL $$ (v. db/schema.sql), sicuro da rilanciare
    ad ogni ripristino mensile del DB di collaudo."""
    with open(os.path.join(BASE_DIR, "db", "schema.sql"), encoding="utf-8") as f:
        sql = f.read()
    if dry_run:
        print(f"[dry-run] Applicherei db/schema.sql ({len(sql)} caratteri) — crea tabelle/tipi/seed di sistema.")
        return
    cur.execute(sql)
    print("Schema applicato su Render (tabelle + seed system_config/matching_algorithm_versions).")


def upsert_riga(cur, tabella: str, pk_col: str, riga: dict, dry_run: bool):
    colonne = list(riga.keys())
    if dry_run:
        return
    placeholders = ", ".join(["%s"] * len(colonne))
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in colonne if c != pk_col)
    # RealDictCursor deserializza le colonne JSONB (es. matches.algoritmo_parametri,
    # i vari psychometric_scores.profilo_*) direttamente in dict Python — psycopg2
    # non sa adattare un dict nudo come parametro, va incapsulato in Json(...)
    # (trovato dal crash reale sul run di produzione: prima colonna JSONB
    # effettivamente valorizzata incontrata dallo script, matches.algoritmo_parametri).
    valori = [psycopg2.extras.Json(riga[c]) if isinstance(riga[c], dict) else riga[c] for c in colonne]
    cur.execute(
        f"INSERT INTO {tabella} ({', '.join(colonne)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({pk_col}) DO UPDATE SET {set_clause}",
        valori,
    )


def copia_tag_embedding_cache(cur_locale, cur_render, dry_run: bool):
    """Passo 2 — dato di riferimento CONDIVISO (non per-utente): senza,
    il pool migrato non troverebbe alcun embedding per i propri tag
    "mi piace/non sopporto" e Punteggio_Tag_Liste degraderebbe in
    silenzio per tutti (v. matching_engine.load_pool)."""
    cur_locale.execute("SELECT tag_normalizzato, embedding_vector, modello_embedding, prima_volta_vista_il FROM tag_embedding_cache")
    righe = cur_locale.fetchall()
    print(f"tag_embedding_cache: {len(righe)} tag da copiare.")
    for r in righe:
        upsert_riga(cur_render, "tag_embedding_cache", "tag_normalizzato", dict(r), dry_run)

    cur_locale.execute("SELECT id, vettore, numero_tag_campione, calcolato_il FROM tag_embedding_centroide")
    centroide = cur_locale.fetchone()
    if centroide:
        print("tag_embedding_centroide: 1 riga da copiare.")
        upsert_riga(cur_render, "tag_embedding_centroide", "id", dict(centroide), dry_run)
    else:
        print("tag_embedding_centroide: nessuna riga in locale, saltato.")


def calcola_offset_ribasamento(cur_locale) -> timedelta | None:
    """I 387 match locali condividono tutti lo stesso identico
    data_proposta (verificato: min == max, un'unica generazione batch
    del 2026-08-13) — l'offset è quindi un singolo valore costante,
    non serve calcolarlo per riga. Sposta quell'istante più recente a
    "ieri" (now - 1 giorno): con finestra_risposta_match_giorni=7,
    lascia una finestra di risposta ancora aperta e credibile per i
    match 'Proposto' invece di uno scarto arbitrario. None se non ci
    sono match in locale (nulla da ribasare)."""
    cur_locale.execute("SELECT max(data_proposta) AS piu_recente FROM matches")
    piu_recente = cur_locale.fetchone()["piu_recente"]
    if piu_recente is None:
        return None
    ancora = datetime.now(timezone.utc) - timedelta(days=1)
    return ancora - piu_recente


# Richiesto esplicitamente per la demo: promuovere qualche "Proposto" a
# "Confermato" arricchisce la Rubrica (oggi 1 sola voce reale) e permette
# di testare POST /feedback su più match. Nota importante, verificata
# leggendo routers/feedback.py e la dashboard prima di scrivere questo
# codice: NON esiste oggi alcuno stato "richiesta feedback in attesa"
# calcolato da nessuna parte (né dashboard né rubrica) — POST /feedback è
# richiamabile in qualunque momento dopo contatto_scambiato=TRUE, senza
# alcun gate sui 15gg né un endpoint che segnali "in attesa". Promuovere
# questi match NON farà quindi comparire un nuovo stato in UI da solo:
# arricchisce solo la Rubrica e rende disponibile la chiamata feedback.
# data_conferma comunque ribasata a >15gg fa come richiesto, per coerenza
# con l'intento (RF-23/24 prevede la richiesta a +15gg dalla chiusura).
N_PROMUOVI_A_CONFERMATO_DEMO = 3


def scegli_match_da_promuovere(cur_locale, righe, n: int) -> set[str]:
    """Solo tra i 'Proposto', e solo se entrambe le parti hanno una foto
    profilo (per una Rubrica visivamente completa in demo) — deterministico
    (ordinati per match_id) per restare stabile su riesecuzioni ripetute."""
    candidati = sorted((r for r in righe if r["stato"] == "Proposto"), key=lambda r: str(r["match_id"]))
    scelti = set()
    for r in candidati:
        if len(scelti) >= n:
            break
        cur_locale.execute(
            "SELECT count(*) AS n FROM physical_profile WHERE user_id IN (%s, %s) AND foto_profilo_url IS NOT NULL",
            (str(r["user_a_id"]), str(r["user_b_id"])),
        )
        if cur_locale.fetchone()["n"] == 2:
            scelti.add(str(r["match_id"]))
    return scelti


def migra_matches(cur_locale, cur_render, dry_run: bool, offset: timedelta | None):
    """Passo 4 — v. docstring del file per il razionale del ribasamento
    date. match_id locale riusato com'è (non un nuovo UUID): mantiene lo
    script idempotente su riesecuzione e preserva la FK di
    match_feedback.match_id senza dover ricostruire una mappa a parte."""
    cur_locale.execute("SELECT * FROM matches ORDER BY data_proposta")
    righe = cur_locale.fetchall()
    print(f"\nmatches: {len(righe)} da migrare"
          + (f" (offset ribasamento: {offset})" if offset else " (nessun offset: nessun match in locale)"))

    promossi = scegli_match_da_promuovere(cur_locale, righe, N_PROMUOVI_A_CONFERMATO_DEMO)
    if promossi:
        print(f"  promossi a 'Confermato' per arricchire la Rubrica demo (sintetico, v. commento nel codice): {sorted(promossi)}")

    per_stato: dict[str, int] = {}
    for r in righe:
        riga = dict(r)
        mid = str(riga["match_id"])
        if mid in promossi:
            ancora_conferma = datetime.now(timezone.utc) - timedelta(days=20)
            riga["stato"] = "Confermato"
            riga["contatto_scambiato"] = True
            riga["pagamento_a_stato"] = "Pagato"
            riga["pagamento_b_stato"] = "Pagato"
            riga["data_proposta"] = ancora_conferma - timedelta(days=2)
            riga["data_scadenza_risposta"] = riga["data_proposta"] + timedelta(days=7)
            riga["data_conferma"] = ancora_conferma
        elif offset:
            riga["data_proposta"] = riga["data_proposta"] + offset
            if riga["data_scadenza_risposta"] is not None:
                riga["data_scadenza_risposta"] = riga["data_scadenza_risposta"] + offset
            if riga["data_conferma"] is not None:
                riga["data_conferma"] = riga["data_conferma"] + offset
        per_stato[riga["stato"]] = per_stato.get(riga["stato"], 0) + 1
        upsert_riga(cur_render, "matches", "match_id", riga, dry_run)

    if dry_run and righe:
        esempio = dict(righe[0])
        print(f"  per stato: {per_stato}")
        if offset:
            print(f"  esempio ribasamento — data_proposta: {esempio['data_proposta']} -> {esempio['data_proposta'] + offset}")
            if esempio["data_scadenza_risposta"] is not None:
                print(f"                        data_scadenza_risposta: {esempio['data_scadenza_risposta']} -> {esempio['data_scadenza_risposta'] + offset}")

    cur_locale.execute("SELECT * FROM match_feedback")
    righe_feedback = cur_locale.fetchall()
    print(f"match_feedback: {len(righe_feedback)} da migrare.")
    for r in righe_feedback:
        riga = dict(r)
        if offset:
            if riga["data_richiesta"] is not None:
                riga["data_richiesta"] = riga["data_richiesta"] + offset
            if riga["data_risposta"] is not None:
                riga["data_risposta"] = riga["data_risposta"] + offset
        if not dry_run:
            colonne = list(riga.keys())
            placeholders = ", ".join(["%s"] * len(colonne))
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in colonne if c not in ("match_id", "user_id"))
            cur_render.execute(
                f"INSERT INTO match_feedback ({', '.join(colonne)}) VALUES ({placeholders}) "
                f"ON CONFLICT (match_id, user_id) DO UPDATE SET {set_clause}",
                [riga[c] for c in colonne],
            )


def reset_pool_demo(cur_render, dry_run: bool):
    if dry_run:
        print("[dry-run] --reset: cancellerei tutte le righe del pool demo già presenti su Render.")
        return
    # match_feedback/matches referenziano users (user_a_id/user_b_id) —
    # vanno cancellati prima delle tabelle satellite/users, altrimenti la
    # FK blocca la DELETE su users.
    cur_render.execute(
        "DELETE FROM match_feedback WHERE match_id IN ("
        "  SELECT match_id FROM matches WHERE user_a_id IN (SELECT user_id FROM users WHERE source_actor_id IS NOT NULL)"
        "     OR user_b_id IN (SELECT user_id FROM users WHERE source_actor_id IS NOT NULL))"
    )
    cur_render.execute(
        "DELETE FROM matches WHERE user_a_id IN (SELECT user_id FROM users WHERE source_actor_id IS NOT NULL)"
        "   OR user_b_id IN (SELECT user_id FROM users WHERE source_actor_id IS NOT NULL)"
    )
    for tabella, _ in reversed(TABELLE_PROFILO_DEMO):
        cur_render.execute(
            f"DELETE FROM {tabella} WHERE user_id IN (SELECT user_id FROM users WHERE source_actor_id IS NOT NULL)"
        )
    cur_render.execute("DELETE FROM users WHERE source_actor_id IS NOT NULL")
    print("Pool demo precedente cancellato da Render (--reset).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    dry_run = args.dry_run

    conn_locale = connetti_locale()
    cur_locale = conn_locale.cursor()

    if dry_run:
        conn_render, cur_render = None, None
        print("=== DRY RUN: nessuna scrittura reale su R2 o Render ===")
        print("Nota: il pool demo locale ha Big Five/Attaccamento/EQ/tag completi, ma")
        print("psychometric_scores.profilo_valori_self (Test Profilo Relazionale, Blocco D)")
        print("è NULL per tutti — mai stato eseguito su questo pool. Verrà copiato NULL")
        print("(fedele alla sorgente), la Coerenza Narrativa userà il fallback neutro 0.5")
        print("per ogni coppia migrata finché non viene colmato separatamente.\n")
    else:
        conn_render = connetti_render()
        cur_render = conn_render.cursor()

    # ── Fase 0-1: estensione + schema ───────────────────────────────────
    if not dry_run:
        abilita_pgvector(cur_render, dry_run)
        conn_render.commit()
        applica_schema(cur_render, dry_run)
        conn_render.commit()
    else:
        abilita_pgvector(None, dry_run)
        applica_schema(None, dry_run)

    if args.reset:
        reset_pool_demo(cur_render, dry_run)
        if not dry_run:
            conn_render.commit()

    # ── Fase 2: dato di riferimento condiviso ───────────────────────────
    if not dry_run:
        copia_tag_embedding_cache(cur_locale, cur_render, dry_run)
        conn_render.commit()
    else:
        copia_tag_embedding_cache(cur_locale, None, dry_run)

    # ── Fase 3: profili demo + foto ─────────────────────────────────────
    # SELECT * (non un elenco a mano) — stessa fedeltà completa già usata
    # per le tabelle satellite sotto, nessuna colonna esclusa in silenzio.
    cur_locale.execute("SELECT * FROM users WHERE source_actor_id IS NOT NULL ORDER BY source_actor_id")
    utenti = cur_locale.fetchall()
    if args.limit:
        utenti = utenti[: args.limit]
    print(f"\nProfili demo da migrare: {len(utenti)}")

    client_r2 = None if dry_run else r2_client()
    foto_caricate, foto_fallite = 0, 0

    for i, u in enumerate(utenti, 1):
        uid = str(u["user_id"])
        if dry_run:
            print(f"\n--- [{i}] {u['nome']} {u['cognome']} ({u['email']}) — user_id={uid} (source_actor_id={u['source_actor_id']}) ---")
        upsert_riga(cur_render, "users", "user_id", dict(u), dry_run)

        # ── foto: profilo + partner ideale, solo se il DB locale dice che esistono ──
        # mai leggere alla cieca dal filesystem per user_id senza controllare
        # prima la colonna DB (lezione già imparata in sessioni precedenti,
        # v. CLAUDE.md — un file può restare su disco anche dopo che il
        # riferimento DB è stato azzerato, es. foto di minori rimosse).
        cur_locale.execute(
            "SELECT foto_profilo_url, foto_partner_ideale_url FROM physical_profile WHERE user_id = %s",
            (uid,),
        )
        foto_row = cur_locale.fetchone()
        url_profilo_r2 = url_pi_r2 = None

        if foto_row and foto_row["foto_profilo_url"]:
            path = os.path.join(STORAGE_DIR, foto_row["foto_profilo_url"])
            if os.path.isfile(path):
                chiave = f"profilo/{uid}.jpg"
                url_profilo_r2 = carica_foto_su_r2(client_r2, path, chiave, dry_run)
                foto_caricate += 1 if url_profilo_r2 else 0
                foto_fallite += 0 if url_profilo_r2 else 1
                if dry_run:
                    print(f"  foto_profilo_url: {foto_row['foto_profilo_url']} -> {url_profilo_r2}")
            else:
                print(f"  [ATTENZIONE] {uid}: DB dice foto profilo presente ma file mancante su disco, saltata.")

        if foto_row and foto_row["foto_partner_ideale_url"]:
            path = os.path.join(STORAGE_DIR, foto_row["foto_partner_ideale_url"])
            if os.path.isfile(path):
                chiave = f"partner_ideale/{uid}.jpg"
                url_pi_r2 = carica_foto_su_r2(client_r2, path, chiave, dry_run)
                foto_caricate += 1 if url_pi_r2 else 0
                foto_fallite += 0 if url_pi_r2 else 1
                if dry_run:
                    print(f"  foto_partner_ideale_url: {foto_row['foto_partner_ideale_url']} -> {url_pi_r2}")
            else:
                print(f"  [ATTENZIONE] {uid}: DB dice foto partner ideale presente ma file mancante su disco, saltata.")

        # ── le 7 tabelle satellite, upsert generico riga-per-riga ───────
        tabelle_presenti = []
        for tabella, pk_col in TABELLE_PROFILO_DEMO:
            cur_locale.execute(f"SELECT * FROM {tabella} WHERE {pk_col} = %s", (uid,))
            riga = cur_locale.fetchone()
            if riga is None:
                continue
            tabelle_presenti.append(tabella)
            riga = dict(riga)
            if tabella == "physical_profile":
                riga["foto_profilo_url"] = url_profilo_r2
                riga["foto_partner_ideale_url"] = url_pi_r2
            upsert_riga(cur_render, tabella, pk_col, riga, dry_run)
        if dry_run:
            mancanti = [t for t, _ in TABELLE_PROFILO_DEMO if t not in tabelle_presenti]
            print(f"  tabelle satellite presenti: {', '.join(tabelle_presenti)}")
            if mancanti:
                print(f"  tabelle satellite ASSENTI in locale (nessuna riga da copiare): {', '.join(mancanti)}")

        if not dry_run and i % 50 == 0:
            conn_render.commit()
            print(f"  {i}/{len(utenti)} profili migrati...")

    if not dry_run:
        conn_render.commit()

    # ── Fase 4: matches + match_feedback (dopo, richiede gli user_id già upsertati) ──
    offset = calcola_offset_ribasamento(cur_locale)
    migra_matches(cur_locale, cur_render, dry_run, offset)
    if not dry_run:
        conn_render.commit()

    print(f"\nCompletato: {len(utenti)} profili {'simulati' if dry_run else 'migrati'}.")
    print(f"Foto: {foto_caricate} caricate su R2, {foto_fallite} fallite.")

    cur_locale.close()
    conn_locale.close()
    if conn_render:
        cur_render.close()
        conn_render.close()


if __name__ == "__main__":
    main()
