"""
generate_narrative_data.py
Genera i due campi liberi RF-07b (profile_narrative.descrizione_di_se /
descrizione_partner_ideale) per i 1000 profili di test — servono a poter
misurare quanto la Coerenza Narrativa (STEP 3, self/ideal embedding
similarity) pesa davvero negli abbinamenti reali, non solo in teoria.

Testo generato per COMBINAZIONE di frasi pescate (RNG seedato su
source_actor_id, riproducibile — stesso pattern di generate_synthetic_data.py)
da banchi di frasi condizionati sui parametri REALI già presenti a DB:

- descrizione_di_se: coerente con Big Five + EQ/maturità + attaccamento
  (ansia/evitamento) + lavoro/città/stile di vita/titolo di studio/fede
  religiosa del profilo.
- descrizione_partner_ideale: coerente con orientamento_sessuale +
  pref_genere_cercato (genere/pronome corretto di chi si immagina) e con i
  criteri soft (figli, fumo/alcol, titolo di studio, corporatura, stato
  civile accettato, religione) — scritta come scena di vita quotidiana
  immaginata, non come lista di aggettivi (v.
  Ainima_Matching_Semantico_Report_v1.md Prompt 3b).

2026-08-19 v2: banchi ampliati (più varianti per bucket + due nuove
dimensioni per lato) e ordine delle frasi centrali mescolato — la prima
versione produceva coerenza narrativa reale ma con spread stretto (0.77-0.82
su un campione di 15 coppie): testi tutti nello stesso registro "profilo da
agenzia" si somigliano nella forma anche quando il contenuto differisce.
Più varianti lessicali + più dimensioni distintive + ordine non fisso
dovrebbero allargare lo spread.

NON esegue qui la pipeline reale (Prompt 3a/3b + embedding Gemini) — quella
resta un passo separato ad alto costo di chiamate API, v.
scripts/run_narrative_pipeline.py.

Uso: python generate_narrative_data.py
"""

import os
import random

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))


def bucket(v, lo=0.4, hi=0.6):
    if v is None:
        return "medio"
    if v < lo:
        return "basso"
    if v > hi:
        return "alto"
    return "medio"


# ── Banchi di frasi: descrizione_di_se ──────────────────────────────────

ESTROVERSIONE = {
    "alto": [
        "Sono una persona solare, mi piace stare in mezzo alla gente e organizzare uscite con gli amici.",
        "Ho bisogno di stare spesso in compagnia, l'energia degli altri mi carica.",
        "Amo conoscere gente nuova, mi viene naturale attaccare bottone quasi con chiunque.",
        "Le serate piene di persone mi fanno stare bene, raramente resto volentieri a casa da sol{ag}.",
        "Difficilmente dico di no a un invito, anche se non conosco quasi nessuno alla festa.",
        "Mi piace essere quella/o che tiene insieme il gruppo, che organizza, che propone di uscire.",
    ],
    "medio": [
        "Mi piace uscire con gli amici, ma so anche godermi una serata tranquilla a casa.",
        "Sono socievole quando serve, ma non ho bisogno di stare sempre in gruppo.",
        "A seconda dei periodi alterno voglia di compagnia e voglia di stare per conto mio.",
        "Con le persone che conosco bene mi apro facilmente, con gli sconosciuti ci metto un po' di più.",
    ],
    "basso": [
        "Preferisco poche persone ma di fiducia, piuttosto che tante conoscenze superficiali.",
        "Ricarico le energie stando da sol{ag}, le grandi feste mi stancano più che divertirmi.",
        "Sono una persona piuttosto riservat{ag}, mi apro solo quando conosco bene qualcuno.",
        "Preferisco una cena in due a una serata affollata.",
        "Le mie giornate migliori sono spesso quelle più tranquille, senza troppi impegni sociali.",
    ],
}

APERTURA = {
    "alto": [
        "Mi piace provare cose nuove, viaggiare in posti che non conosco e uscire dalla routine.",
        "Sono curios{ag} per natura, leggo e mi informo su argomenti molto diversi tra loro.",
        "Cambiare piani all'ultimo momento non mi spaventa, anzi mi piace l'imprevisto.",
        "Mi incuriosiscono le prospettive diverse dalla mia, mi piace mettere in discussione quello che do per scontato.",
        "Ho sempre un progetto nuovo per la testa, che sia un viaggio, un corso o un hobby mai provato prima.",
    ],
    "medio": [
        "Apprezzo le novità ma anche avere dei punti fermi nella settimana.",
        "Mi piace variare, senza però stravolgere troppo spesso le mie abitudini.",
        "Sono apert{ag} alle novità che hanno senso per me, meno a cambiare tanto per cambiare.",
    ],
    "basso": [
        "Preferisco la stabilità: so cosa mi piace e tendo a restarci fedele.",
        "Mi trovo bene con una routine chiara, le grandi novità mi mettono un po' a disagio.",
        "Non sento il bisogno di cambiare spesso: quando qualcosa funziona, perché cambiarla?",
        "Sono una persona pratica più che sognatrice, mi fido di ciò che conosco già.",
    ],
}

MATURITA_EMOTIVA = {
    "alto": [
        "Nei momenti difficili riesco quasi sempre a mantenere la calma e a pensare con lucidità.",
        "Ho imparato a riconoscere le mie emozioni prima che prendano il sopravvento.",
        "Quando sono sotto stress cerco di fermarmi un attimo prima di reagire d'istinto.",
        "Con gli anni ho imparato a non prendere le cose sul personale quando non serve.",
    ],
    "medio": [
        "Non sono sempre lucidissim{ag} sotto pressione, ma con il tempo riesco a rimettere ordine nei pensieri.",
        "Ci sono giorni in cui gestisco tutto con calma e altri in cui fatico di più — è normale, credo.",
        "Sto lavorando sul mio modo di reagire alle difficoltà, con qualche passo avanti e qualche ricaduta.",
    ],
    "basso": [
        "Quando sono sotto pressione faccio più fatica del solito a restare lucid{ag}.",
        "Le emozioni forti a volte mi travolgono prima che riesca a capire bene cosa sta succedendo.",
        "Sto ancora imparando a gestire i momenti di tensione senza farmi prendere troppo.",
        "Non sono ancora bravissim{ag} a gestire lo stress, ci sto lavorando.",
    ],
}

# gradevolezza + coscienziosità -> stile relazionale nei conflitti/impegni
GRADEVOLEZZA_COSCIENZIOSITA = {
    ("alto", "alto"): [
        "Nelle discussioni cerco sempre un punto d'incontro, e tengo molto a mantenere gli impegni presi.",
        "Sono una persona affidabile e mi piace pensare di essere anche facile da avere accanto.",
    ],
    ("alto", "basso"): [
        "Sono una persona accomodante, anche se organizzarmi non è sempre il mio forte.",
        "Preferisco evitare gli scontri, anche a costo di improvvisare un po' di più del previsto.",
    ],
    ("basso", "alto"): [
        "Sono molto organizzat{ag} e dirett{ag}, dico quello che penso anche quando non è comodo.",
        "Tengo molto agli impegni presi, e nelle discussioni non ho paura di far valere la mia posizione.",
    ],
    ("basso", "basso"): [
        "Non amo particolarmente i compromessi, e l'organizzazione non è il mio forte.",
        "Tendo a dire quello che penso senza troppi giri di parole, anche se poi improvviso parecchio.",
    ],
    "default": [
        "Nelle relazioni cerco un equilibrio tra dire quello che penso e venire incontro all'altra persona.",
    ],
}

ATTACCAMENTO_SELF = {
    ("basso", "basso"): [  # ansia bassa, evitamento basso -> sicuro
        "Nelle relazioni mi sento abbastanza sicur{ag}: mi fido facilmente e non ho paura di aprirmi.",
        "Riesco a stare bene sia in coppia sia per conto mio, senza troppa ansia o troppa distanza.",
    ],
    ("alto", "basso"): [  # ansioso
        "Nelle relazioni tengo molto alla vicinanza, e a volte ho bisogno di qualche rassicurazione in più.",
        "Sono una persona che si affeziona intensamente, mi piace sentire il partner vicino anche nei piccoli gesti quotidiani.",
    ],
    ("basso", "alto"): [  # evitante
        "Tengo molto alla mia indipendenza, anche dentro una relazione ho bisogno dei miei spazi.",
        "Non sono un tipo che si apre subito: mi ci vuole tempo prima di condividere davvero le mie cose.",
    ],
    ("alto", "alto"): [  # timoroso/disorganizzato
        "Nelle relazioni convivono in me il desiderio di vicinanza e la voglia di proteggermi un po' — sto ancora imparando a bilanciare le due cose.",
    ],
    "default": [
        "Nelle relazioni cerco un equilibrio sano tra vicinanza e indipendenza.",
    ],
}

# nuova dimensione: titolo di studio -> come parla del proprio percorso
TITOLO_STUDIO_SELF = {
    "Dottorato di ricerca": [
        "Ho fatto un dottorato, e mi porto dietro l'abitudine di approfondire tutto fino in fondo.",
        "Vengo dal mondo della ricerca, e mi capita di applicare lo stesso approccio anche fuori dal lavoro.",
    ],
    "Laurea magistrale": [
        "Ho studiato parecchio, e mi piace ancora tenermi aggiornat{ag} su quello che mi interessa.",
    ],
    "Laurea triennale": [],
    "Diploma superiore": [
        "Non ho un percorso di studi lunghissimo, ma ho imparato molto sul campo.",
    ],
    None: [],
}

# nuova dimensione: fede/importanza religione -> quanto ne parla di sé.
# fede_religiosa in DB è salvata in forma FEMMINILE canonica (es. "Ebraica",
# "Cristiana cattolica") indipendentemente dal genere della persona — corretto
# solo quando modifica il sostantivo "fede" ("la fede ebraica" resta femminile
# sempre), sbagliato in "Sono {fede}" dove l'aggettivo riferisce alla persona
# e deve accordarsi al SUO genere. "Nessuna"/"Altra" non hanno una forma a
# singola parola sensata in "Sono ..." e restano escluse da quella frase.
FEDE_MASCHILE = {
    "Agnostica": "Agnostico", "Atea": "Ateo", "Buddista": "Buddista",
    "Cristiana cattolica": "Cristiano cattolico", "Cristiana ortodossa": "Cristiano ortodosso",
    "Cristiana protestante": "Cristiano protestante", "Ebraica": "Ebraico",
    "Induista": "Induista", "Islamica": "Islamico",
}

FEDE_SELF = {
    "alta": [
        "La fede {fede} ha un posto importante nella mia vita di tutti i giorni.",
        "Sono {fede_ag}, e per me non è solo una tradizione, la vivo attivamente.",
    ],
    "media": [
        "Sono {fede_ag}, senza che sia il centro della mia vita.",
    ],
    "bassa": [],
}

STILE_VITA_CHIUSURA = [
    "Nel tempo libero mi piace {sport}.",
    "Quando posso, {sport}.",
    "Fuori dal lavoro dedico parecchio tempo a {sport}.",
    "Una delle cose che faccio più volentieri, appena ho tempo, è {sport}.",
]

FIGLI_CHIUSURA = {
    True: [
        "Ho già dei figli, ed è una delle parti più importanti della mia vita.",
        "Sono genitore, e questo dice molto su come organizzo le mie giornate.",
    ],
    False: [],
}

# ── Amo/odio — dettagli concreti e idiosincratici (non legati a nessun
# campo strutturato in DB, seedati per utente) — su richiesta esplicita:
# il testo generico basato solo sui tratti psicometrici produceva testi
# troppo simili nella forma; un gusto specifico ("odio i gatti, amo il
# biliardo") dovrebbe differenziare gli embedding molto di più.
# Voci "ambivalenti" — una persona vera potrebbe plausibilmente amarle O
# odiarle (i gatti li si ama o si odia, dipende da chi scrivi).
TEMI_AMBIVALENTI = [
    "i gatti", "i cani", "il biliardo", "viaggiare", "cucinare", "il mare",
    "la montagna", "leggere", "ballare", "correre", "i concerti dal vivo",
    "gli scacchi", "il buon vino", "i mercatini dell'usato", "la fotografia",
    "andare in bici", "il trekking", "i musei", "la pizza", "i tramonti",
    "la palestra", "i film horror", "i reality show", "il karaoke",
    "i cruciverba", "il cinema", "la cucina piccante", "i giochi da tavolo",
    "il giardinaggio", "le maratone di serie tv", "il buon caffè", "i social network",
]
# Voci quasi sempre negative — sensate solo come bersaglio di "odio", mai
# di "amo" (nessuno scrive davvero "amo le file lunghe" in un profilo).
TEMI_SOLO_NEGATIVI = [
    "le file lunghe", "la mancanza di puntualità", "il rumore del traffico",
    "le bugie", "il caldo estremo", "i mezzi pubblici affollati",
    "chi non risponde ai messaggi", "il freddo pungente",
    "chi parla ad alta voce al telefono",
]


def genera_amore_odio(rng):
    odio = rng.choice(TEMI_AMBIVALENTI + TEMI_SOLO_NEGATIVI)
    amo = rng.choice([t for t in TEMI_AMBIVALENTI if t != odio])
    if rng.random() < 0.5:
        return f"Odio {odio}, amo {amo}."
    return f"Amo {amo}, odio {odio}."


def _ag(genere):
    """Suffisso di accordo aggettivo (o/a) in base al genere reale della persona."""
    return "o" if genere == "Maschile" else "a"


def genera_descrizione_di_se(rng, dati):
    ag = _ag(dati["genere"])
    frasi_centrali = []

    frasi_centrali.append(rng.choice(ESTROVERSIONE[bucket(dati["estroversione"])]).format(ag=ag))
    frasi_centrali.append(rng.choice(APERTURA[bucket(dati["apertura"])]).format(ag=ag))
    frasi_centrali.append(rng.choice(MATURITA_EMOTIVA[bucket(dati["maturita"])]).format(ag=ag))

    chiave_gc = (bucket(dati["gradevolezza"]), bucket(dati["coscienziosita"]))
    banco_gc = GRADEVOLEZZA_COSCIENZIOSITA.get(chiave_gc, GRADEVOLEZZA_COSCIENZIOSITA["default"])
    frasi_centrali.append(rng.choice(banco_gc).format(ag=ag))

    chiave_att = (bucket(dati["ansia"]), bucket(dati["evitamento"]))
    banco_att = ATTACCAMENTO_SELF.get(chiave_att, ATTACCAMENTO_SELF["default"])
    frasi_centrali.append(rng.choice(banco_att).format(ag=ag))

    banco_studio = TITOLO_STUDIO_SELF.get(dati["titolo_studio"], [])
    if banco_studio:
        frasi_centrali.append(rng.choice(banco_studio).format(ag=ag))

    importanza = dati["importanza_religione"]
    fede = dati["fede_religiosa"]
    if fede and fede not in ("Nessuna", "Altra") and importanza is not None:
        fede_ag = fede if dati["genere"] != "Maschile" else FEDE_MASCHILE.get(fede, fede)
        livello = "alta" if importanza >= 4 else ("media" if importanza >= 2 else "bassa")
        banco_fede = FEDE_SELF[livello]
        if banco_fede:
            frasi_centrali.append(rng.choice(banco_fede).format(fede=fede, fede_ag=fede_ag))

    if dati["stile_vita_sport"]:
        frasi_centrali.append(rng.choice(STILE_VITA_CHIUSURA).format(sport=dati["stile_vita_sport"]))
    if dati["ha_figli"]:
        frasi_centrali.append(rng.choice(FIGLI_CHIUSURA[True]))

    frasi_centrali.append(genera_amore_odio(rng))

    # l'apertura scelta apposta per il primo giro resta prima (framing
    # naturale "chi sono/dove vivo"), il resto è mescolato — più varietà
    # strutturale oltre che lessicale tra un profilo e l'altro.
    rng.shuffle(frasi_centrali)

    comune = dati["comune_residenza"] or "zona Milano"
    settore = dati["settore_occupazionale"]
    apertura = f"Vivo a {comune} e lavoro nel settore {settore}." if settore else f"Vivo a {comune}."

    return " ".join([apertura] + frasi_centrali)


# ── Banchi di frasi: descrizione_partner_ideale ─────────────────────────
# Scena di vita immaginata (non lista di aggettivi), coerente col genere
# realmente cercato (RF-08/dealbreaker) — mai neutra per pigrizia quando
# un genere è dichiarato, per rispettare "gusti sessuali" reali del profilo.

def pronomi(genere_cercato):
    if genere_cercato == "Maschile":
        return {"sogg": "lui", "poss": "suo", "art": "il", "agg_o_a": "o", "persona": "un uomo"}
    if genere_cercato == "Femminile":
        return {"sogg": "lei", "poss": "sua", "art": "la", "agg_o_a": "a", "persona": "una donna"}
    return {"sogg": "questa persona", "poss": "sua", "art": "la", "agg_o_a": "a", "persona": "una persona"}


SCENA_APERTURA = [
    "Mi immagino {persona} con cui la domenica mattina si fa colazione con calma, senza fretta di alzarsi.",
    "Penso spesso a una serata in cui si cucina insieme, ridendo di come è andata la giornata.",
    "Mi vedo con {persona} che ha voglia di fare una passeggiata la sera, parlando di tutto e di niente.",
    "Immagino un weekend in cui si sceglie insieme cosa fare, senza dover decidere sempre da sol{ag_self}.",
    "Mi piace pensare a un viaggio organizzato insieme all'ultimo momento, senza troppi piani.",
    "Mi immagino un pomeriggio qualsiasi, ognuno per conto suo in casa ma con la porta aperta tra le stanze.",
]

SCENA_DINAMICA_ANSIA = {  # dinamica desiderata in base al PROPRIO attaccamento
    "alto": [  # ansioso -> cerca vicinanza/rassicurazione
        "Mi piacerebbe una persona presente, che sappia farmi sentire al sicuro anche nei momenti di silenzio.",
        "Cerco qualcuno con cui i piccoli gesti quotidiani — un messaggio, una chiamata — non manchino mai.",
        "Vorrei sentire che per {sogg} sono una priorità, non solo un'opzione tra tante.",
    ],
    "medio": [
        "Mi piacerebbe una persona presente, ma senza che diventi una dipendenza da entrambe le parti.",
        "Cerco un equilibrio: vicinanza vera, senza bisogno di sentirci ogni ora.",
    ],
    "basso": [
        "Cerco qualcuno con cui stare bene senza bisogno di continue conferme, in modo naturale.",
        "Non ho bisogno di rassicurazioni costanti, mi basta sapere che ci si sceglie ogni giorno.",
    ],
}
SCENA_DINAMICA_EVITAMENTO = {  # in base al PROPRIO evitamento
    "alto": [
        "Apprezzerei una persona che rispetti i miei spazi, senza sentirsi trascurata se ogni tanto ho bisogno di stare per conto mio.",
        "Mi piacerebbe una relazione che lasci spazio anche a interessi e amicizie separate.",
    ],
    "medio": [
        "Mi piacerebbe un buon equilibrio tra condividere le cose e rispettare i tempi di ciascuno.",
    ],
    "basso": [
        "Mi piacerebbe condividere davvero tutto, anche le cose più piccole della giornata.",
        "Immagino una relazione dove ci si racconta i dettagli, non solo le cose importanti.",
    ],
}

SCENA_FIGLI = {
    "Si": [
        "Nella scena che immagino ci sono anche dei bambini, è una parte importante del futuro che vorrei.",
        "Mi immagino una famiglia con figli, è qualcosa a cui tengo davvero.",
    ],
    "No": ["Non immagino figli in questo futuro, mi vedo bene anche senza."],
    "Indifferente": [],
    "Da valutare": ["Non ho ancora le idee chiarissime sui figli, ma vorrei poterne parlare con calma con questa persona."],
}

SCENA_STUDIO = {
    "Laurea magistrale": ["Mi piace immaginar{lo_la} come una persona a cui piace approfondire, studiare, capire le cose fino in fondo."],
    "Dottorato": ["Mi piace immaginar{lo_la} come una persona a cui piace approfondire, studiare, capire le cose fino in fondo."],
    "Laurea triennale": [],
    "Diploma": [],
    "Altro": [],
    None: [],
}

SCENA_CORPORATURA = {
    "Atletica": ["Mi piace immaginar{lo_la} come una persona attiva, a cui piace muoversi."],
    "Snella": [],
    "Media": [],
    "Robusta": [],
    "Curvy": [],
    None: [],
}

SCENA_STATO_CIVILE = {
    "Divorziato/a": ["Non mi pesa che abbia già avuto un matrimonio alle spalle, anzi porta esperienza."],
    "Vedovo/a": [],
    "Celibe/Nubile": [],
    "Separato/a": [],
    None: [],
}

SCENA_FUMO_ALCOL = {
    (False, False): ["Preferirei una vita abbastanza sana insieme, niente sigarette né grandi bevute."],
    (False, True): ["Non mi dispiacerebbe qualche bicchiere in compagnia, ma niente fumo."],
    (True, False): [],
    (True, True): [],
}

SCENA_RELIGIONE = [
    "Vorrei poter condividere con {sogg} anche le cose importanti, i valori in cui credo.",
    "Mi piacerebbe che {sogg} desse valore alle stesse cose a cui tengo io.",
]

# ── Amo/odio sul partner immaginato — attività condivise desiderate +
# un difetto caratteriale che non tollererei (dettaglio concreto, non
# legato a nessun campo strutturato, seedato per utente — stesso principio
# di TEMI_PERSONALI sopra, ma qui il "odio" è su un tratto di carattere
# dell'altra persona, non un gusto personale).
PARTNER_ATTIVITA = [
    "viaggiare", "passeggiare per i boschi", "cucinare insieme", "il mare",
    "la montagna", "gli animali", "leggere", "la musica dal vivo", "ballare",
    "lo sport all'aperto", "l'arte", "i viaggi organizzati all'ultimo momento",
    "la buona cucina", "il cinema", "scoprire posti nuovi", "gli scacchi",
    "il buon vino", "la fotografia", "andare in bici", "il trekking",
]

PARTNER_DIFETTI = [
    "le persone false", "la maleducazione", "chi non mantiene la parola data",
    "l'arroganza", "la gelosia eccessiva", "le bugie", "chi giudica senza conoscere",
    "la superficialità", "l'egoismo", "chi non ha rispetto per gli altri",
    "chi non si assume le proprie responsabilità", "la scortesia gratuita",
]


def genera_amore_odio_partner(rng):
    attivita = rng.sample(PARTNER_ATTIVITA, 2)
    difetto = rng.choice(PARTNER_DIFETTI)
    return f"Vorrei una persona che ama {attivita[0]} e {attivita[1]}. Odio {difetto}."


def genera_descrizione_partner_ideale(rng, dati):
    p = pronomi(dati["pref_genere_cercato"])
    ag_self = _ag(dati["genere"])  # riferito a chi scrive, non al partner immaginato
    frasi = []

    apertura = rng.choice(SCENA_APERTURA)
    frasi.append(apertura.format(persona=p["persona"], ag_self=ag_self))

    frasi.append(rng.choice(SCENA_DINAMICA_ANSIA[bucket(dati["ansia"])]).format(sogg=p["sogg"]))
    frasi.append(rng.choice(SCENA_DINAMICA_EVITAMENTO[bucket(dati["evitamento"])]))

    if dati["pref_accetta_figli"] in ("Si",) or dati["pref_desidera_figli_futuri"] in SCENA_FIGLI:
        chiave_figli = dati["pref_desidera_figli_futuri"]
        for f in SCENA_FIGLI.get(chiave_figli, []):
            frasi.append(f)

    banco_studio = SCENA_STUDIO.get(dati["pref_titolo_studio"], [])
    if banco_studio:
        frasi.append(rng.choice(banco_studio).format(lo_la="lo" if p["agg_o_a"] == "o" else "la"))

    banco_corp = SCENA_CORPORATURA.get(dati["pref_corporatura"], [])
    if banco_corp:
        frasi.append(rng.choice(banco_corp).format(lo_la="lo" if p["agg_o_a"] == "o" else "la"))

    banco_sc = SCENA_STATO_CIVILE.get(dati["pref_stato_civile_accettato"], [])
    if banco_sc:
        frasi.append(rng.choice(banco_sc))

    if dati["pref_fumo"] is not None and dati["pref_alcol"] is not None:
        for f in SCENA_FUMO_ALCOL.get((dati["pref_fumo"], dati["pref_alcol"]), []):
            frasi.append(f)

    if dati["pref_importanza_religione"] is not None and dati["pref_importanza_religione"] >= 3:
        frasi.append(rng.choice(SCENA_RELIGIONE).format(sogg=p["sogg"]))

    # stessa logica del lato "di sé": la prima frase inquadra la scena,
    # il resto viene mescolato per variare la struttura tra un profilo e l'altro.
    resto = frasi[1:]
    rng.shuffle(resto)
    return " ".join([frasi[0]] + resto + [genera_amore_odio_partner(rng)])


def main():
    conn = psycopg2.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.source_actor_id, u.ha_figli, u.genere,
               s.comune_residenza, s.settore_occupazionale, s.titolo_studio,
               s.fede_religiosa, s.importanza_religione,
               p.stile_vita_sport,
               d.pref_genere_cercato, d.pref_accetta_figli, d.pref_desidera_figli_futuri,
               sc.pref_titolo_studio, sc.pref_corporatura, sc.pref_stato_civile_accettato,
               sc.pref_fumo, sc.pref_alcol, sc.pref_importanza_religione,
               ps.score_big5_estroversione AS estroversione, ps.score_big5_gradevolezza AS gradevolezza,
               ps.score_big5_coscienziosita AS coscienziosita, ps.score_big5_apertura AS apertura,
               ps.score_maturita_emotiva AS maturita, ps.ansia_score AS ansia, ps.evitamento_score AS evitamento
        FROM users u
        JOIN socio_profile s ON s.user_id = u.user_id
        JOIN physical_profile p ON p.user_id = u.user_id
        JOIN dealbreaker_criteria d ON d.user_id = u.user_id
        JOIN soft_criteria sc ON sc.user_id = u.user_id
        JOIN psychometric_scores ps ON ps.user_id = u.user_id
        WHERE u.source_actor_id IS NOT NULL
        ORDER BY u.source_actor_id
    """)
    rows = cur.fetchall()
    print(f"Profili da completare: {len(rows)}")

    n_scritti = 0
    for r in rows:
        seed = r["source_actor_id"] * 7919 + 3  # offset per non correlare con generate_synthetic_data.py
        rng = random.Random(seed)

        descrizione_di_se = genera_descrizione_di_se(rng, r)
        descrizione_partner_ideale = genera_descrizione_partner_ideale(rng, r)

        cur.execute("""
            INSERT INTO profile_narrative (user_id, descrizione_di_se, descrizione_partner_ideale, data_ultima_modifica)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                descrizione_di_se = EXCLUDED.descrizione_di_se,
                descrizione_partner_ideale = EXCLUDED.descrizione_partner_ideale,
                data_ultima_modifica = now()
        """, (str(r["user_id"]), descrizione_di_se, descrizione_partner_ideale))
        n_scritti += 1

    conn.commit()
    print(f"Completato: {n_scritti} profili aggiornati.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
