"""Adegua data_nascita dei profili demo all'età apparente nella foto profilo
(stima AWS Rekognition, Attributes=['ALL'] -> AgeRange), richiesto
esplicitamente dall'utente dopo aver notato che l'età dichiarata dei
profili demo appare spesso scollegata dalla foto (v. CLAUDE.md — test su
20 foto: 14/20 con differenza di anche +30/+50 anni tra età DB e stima
Rekognition).

Nessun backup dei valori originali (istruzione esplicita dell'utente:
"erano valori di test"). Solo foto_profilo_url (non foto_partner_ideale) —
altra istruzione esplicita. Solo profili demo (is_demo = TRUE) con
foto_profilo_url NOT NULL — i 99 profili senza foto profilo (rimossi
durante la pulizia minori, v. CLAUDE.md 2026-09-05) sono lasciati
INVARIATI qui: la generazione di una nuova foto via modello generativo è
un passo separato, non ancora deciso/costruito in questo progetto.

Nuova data_nascita = 1° gennaio dell'anno corrispondente al PUNTO MEDIO
del range Rekognition (Low+High)/2 — Rekognition non dà un'età precisa,
solo un intervallo, quindi giorno/mese sono arbitrari per costruzione.

Rate limiting conservativo (0.4s tra una chiamata e l'altra, verificato
dal vivo su un campione di 20 foto: zero throttling a questo ritmo) +
retry con backoff esponenziale su ThrottlingException/
ProvisionedThroughputExceededException, per non dipendere dal
conoscere il quota esatto dell'account (le credenziali AWS usate in
questo progetto non hanno permessi su ServiceQuotas per leggerlo).

Aggiorna SEMPRE sia il DB locale sia Render nella stessa esecuzione (non
due run separati): la stima Rekognition viene calcolata UNA sola volta per
foto e applicata a entrambi i database, dato che sono la stessa foto su R2
per entrambi — dimezza le chiamate AWS rispetto a due passate separate.
Il DB locale è la lista di riferimento (query iniziale), l'aggiornamento
su Render usa lo stesso user_id.

Uso:
    python scripts/adegua_eta_a_foto_profilo.py
"""

import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

PAUSA_SECONDI = 0.4
TENTATIVI_MASSIMI = 4


def main():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

    import boto3
    import psycopg2
    import psycopg2.extras
    from botocore.exceptions import ClientError

    from db import get_conn  # noqa: E402
    from services.photo_storage import get_photo_storage

    conn_locale = get_conn()
    conn_render = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)

    cur = conn_locale.cursor()
    cur.execute("""
        SELECT u.user_id, u.nome, u.cognome,
               EXTRACT(YEAR FROM age(u.data_nascita))::int AS eta_attuale,
               p.foto_profilo_url
        FROM users u JOIN physical_profile p ON p.user_id = u.user_id
        WHERE u.is_demo = TRUE AND p.foto_profilo_url IS NOT NULL
        ORDER BY u.source_actor_id
    """)
    righe = cur.fetchall()
    print(f"Profili da elaborare: {len(righe)}")

    storage = get_photo_storage(os.path.join(os.path.dirname(__file__), "..", "storage", "photos"))
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client(
        "rekognition", region_name=region,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    def rileva_con_retry(contenuto):
        attesa = PAUSA_SECONDI
        for tentativo in range(TENTATIVI_MASSIMI):
            try:
                return client.detect_faces(Image={"Bytes": contenuto}, Attributes=["ALL"])
            except ClientError as e:
                codice = e.response["Error"]["Code"]
                if codice in ("ThrottlingException", "ProvisionedThroughputExceededException") and tentativo < TENTATIVI_MASSIMI - 1:
                    print(f"  [throttling, ritento tra {attesa}s]")
                    time.sleep(attesa)
                    attesa *= 2
                    continue
                raise

    aggiornati = 0
    saltati = 0
    errori = 0

    for i, r in enumerate(righe, start=1):
        nome = f"{r['nome']} {r['cognome']}"
        try:
            contenuto = storage.leggi(r["foto_profilo_url"])
            risposta = rileva_con_retry(contenuto)
            volti = risposta.get("FaceDetails", [])
            if not volti:
                print(f"[{i}/{len(righe)}] {nome}: nessun volto rilevato, saltato")
                saltati += 1
                continue
            volto = max(volti, key=lambda v: v["Confidence"])
            eta_range = volto["AgeRange"]
            # Clamp a 18 (istruzione esplicita dell'utente, dopo verifica
            # visuale manuale su 2 casi con stima Rekognition <18 risultati
            # essere falsi positivi, non minori veri): non si scrive mai
            # un'età sotto i 18 anni, a prescindere dalla stima del
            # servizio — l'obiettivo è chiudere la bonifica dati, non
            # inseguire una precisione che Rekognition non garantisce su
            # volti sintetici GAN.
            punto_medio = max(18, round((eta_range["Low"] + eta_range["High"]) / 2))
            anno_nascita = date.today().year - punto_medio
            nuova_data_nascita = date(anno_nascita, 1, 1)

            cur_locale = conn_locale.cursor()
            cur_locale.execute("UPDATE users SET data_nascita = %s WHERE user_id = %s",
                                (nuova_data_nascita, r["user_id"]))
            conn_locale.commit()
            cur_render = conn_render.cursor()
            cur_render.execute("UPDATE users SET data_nascita = %s WHERE user_id = %s",
                                (nuova_data_nascita, r["user_id"]))
            conn_render.commit()
            print(f"[{i}/{len(righe)}] {nome}: {r['eta_attuale']} -> {punto_medio} "
                  f"(Rekognition {eta_range['Low']}-{eta_range['High']})")
            aggiornati += 1
        except Exception as e:
            print(f"[{i}/{len(righe)}] {nome}: ERRORE, saltato ({e})")
            errori += 1
        time.sleep(PAUSA_SECONDI)

    print()
    print(f"Completato. Aggiornati: {aggiornati}, saltati (nessun volto): {saltati}, errori: {errori}")
    conn_locale.close()
    conn_render.close()


if __name__ == "__main__":
    main()
