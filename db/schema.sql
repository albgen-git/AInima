-- ============================================================
--  Ainima — Schema PostgreSQL (MVP)
--  Basato su Documento_Requisiti_v1.md §7, aggiornato con le
--  decisioni di congruenza del 2026-08-12 (v. CLAUDE.md).
--
--  NOTA pgvector: non ancora installato su questo sistema (v.
--  CLAUDE.md). Gli embedding sono temporaneamente DOUBLE PRECISION[]
--  invece di VECTOR(n); andranno migrati a VECTOR quando l'estensione
--  sarà disponibile, per abilitare la similarity search indicizzata.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

-- ------------------------------------------------------------
-- Tipi enumerati
-- ------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE genere_enum AS ENUM ('Maschile','Femminile','Non binario','Altro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE orientamento_enum AS ENUM ('Eterosessuale','Omosessuale','Bisessuale','Pansessuale','Asessuale','Altro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 'In attesa - verifica moderazione' aggiunto per RF-06b/RF-09 (v.
-- Documento_Requisiti_v1.md, versione con moderazione contenuti fotografici)
DO $$ BEGIN
    CREATE TYPE stato_account_enum AS ENUM ('In attesa','In attesa - verifica moderazione','Attivo','Sospeso','Chiuso');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE livello_abbonamento_enum AS ENUM ('Free','Basic','Premium');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE stato_match_enum AS ENUM ('Proposto','Accettato_A','Accettato_B','Confermato','Rifiutato','Scaduto');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ------------------------------------------------------------
-- §7.1 Identità e Account
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- nome/cognome/data_nascita/genere/orientamento_sessuale sono NULLABLE:
    -- l'account nasce con la sola email (v. RF-02/RF-02b in
    -- Documento_Requisiti_v1_2.md — autenticazione via email OTP, niente
    -- password), il resto si compila progressivamente negli step successivi
    -- del wizard (v. CLAUDE.md).
    nome                        VARCHAR(80),
    cognome                     VARCHAR(80),
    email                       VARCHAR(255) UNIQUE NOT NULL,
    email_verificata            BOOLEAN NOT NULL DEFAULT FALSE,
    -- telefono autodichiarato, MAI verificato in questa fase (RF-02b,
    -- decisione esplicita di costo) — niente più telefono_verificato.
    telefono                    VARCHAR(30),
    data_nascita                DATE,
    genere                      genere_enum,
    orientamento_sessuale       orientamento_enum,
    stato_civile                VARCHAR(30),
    ha_figli                    BOOLEAN,
    stato_account                stato_account_enum NOT NULL DEFAULT 'In attesa',
    livello_abbonamento         livello_abbonamento_enum NOT NULL DEFAULT 'Free',
    data_scadenza_abbonamento   DATE,
    metodo_pagamento_token      VARCHAR(255),
    consenso_dati_sensibili     BOOLEAN NOT NULL DEFAULT FALSE,
    consenso_dati_sensibili_at  TIMESTAMPTZ,
    -- predisposizione multi-mercato (decisione Dubai: "predisponi ma non costruire", v. CLAUDE.md)
    mercato                     VARCHAR(20) NOT NULL DEFAULT 'Milano',
    valuta                      VARCHAR(3)  NOT NULL DEFAULT 'EUR',
    locale                      VARCHAR(5)  NOT NULL DEFAULT 'it-IT',
    data_creazione               TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- tracciabilità per import dati di test dal DB Actor (non fa parte dello schema di produzione)
    source_actor_id             INT UNIQUE
);

-- ------------------------------------------------------------
-- Autenticazione via email OTP (RF-02, Documento_Requisiti_v1_2.md) — un
-- solo codice attivo per email (nuova richiesta sovrascrive la precedente),
-- codice SEMPRE hashato (mai in chiaro a DB, v. security.py hash_otp).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS otp_codes (
    email              VARCHAR(255) PRIMARY KEY,
    codice_hash        VARCHAR(255) NOT NULL,
    scade_il           TIMESTAMPTZ NOT NULL,
    tentativi          INTEGER NOT NULL DEFAULT 0,
    creato_il          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- §7.2 Profilo fisico
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS physical_profile (
    user_id                         UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    altezza_cm                      SMALLINT,
    peso_kg                         NUMERIC(5,1),
    corporatura                     VARCHAR(30),
    colore_capelli                  VARCHAR(30),
    colore_occhi                    VARCHAR(30),
    fumo                            BOOLEAN,
    alcol                           BOOLEAN,
    stile_vita_sport                VARCHAR(40),
    foto_profilo_url                VARCHAR(255),
    foto_partner_ideale_url         VARCHAR(255),
    -- embedding visivo ArcFace (512-dim). RF-11a/RF-11b: sceglie SEMPRE il
    -- vincitore tra la shortlist di dimensione_shortlist_analisi_visiva
    -- candidati già filtrati/ordinati per compatibilità caratteriale — mai
    -- usato per formare la shortlist stessa, né per bypassare i filtri hard.
    embedding_visivo_profilo         DOUBLE PRECISION[],
    embedding_visivo_partner_ideale  DOUBLE PRECISION[]
);

-- ------------------------------------------------------------
-- §7.3 Profilo socio-economico
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS socio_profile (
    user_id                 UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    comune_residenza        VARCHAR(100),
    coordinate_gps           POINT,
    titolo_studio            VARCHAR(50),
    settore_occupazionale    VARCHAR(60),
    fascia_reddito           VARCHAR(40), -- extra rispetto a Documento_Requisiti, presente nel dataset Actors DB
    fede_religiosa           VARCHAR(50),
    importanza_religione     SMALLINT,
    -- v. Ainima_Algoritmo_Ranking_Finale_v1.md §3bis/§9: sostituiscono
    -- pref_distanza_max_km (superato) per le coppie oltre soglia_area_urbana_km.
    importanza_vicinanza_geografica REAL, -- normalizzata 0.0-1.0, da domanda Likert 1-5 in onboarding
    lingue_parlate           TEXT[]       -- lingue in cui la persona può sostenere una relazione
);

-- ------------------------------------------------------------
-- §7.4 Criteri di ricerca — split esplicito dealbreaker / soft
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dealbreaker_criteria (
    user_id                      UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    pref_genere_cercato           genere_enum,
    pref_orientamento_compatibile orientamento_enum,
    pref_eta_min                  SMALLINT,
    pref_eta_max                  SMALLINT,
    -- pref_distanza_max_km RIMOSSO — SUPERATO per
    -- Ainima_00_Indice_Schema_Consolidato_v1.md §3.2: un tetto fisso in km
    -- uguale per tutti è stato abbandonato, sostituito dalla logica
    -- combinata in socio_profile.importanza_vicinanza_geografica +
    -- socio_profile.lingue_parlate + system_config.soglia_area_urbana_km
    -- (v. matching_engine.hard_filters_ok e Algoritmo_Ranking_Finale §3bis).
    pref_accetta_figli            VARCHAR(15), -- 'Si' | 'No' | 'Indifferente'
    pref_desidera_figli_futuri    VARCHAR(15)  -- 'Si' | 'No' | 'Da valutare'
);

CREATE TABLE IF NOT EXISTS soft_criteria (
    user_id                   UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    pref_altezza_min           SMALLINT,
    pref_altezza_max           SMALLINT,
    pref_stato_civile_accettato VARCHAR(30),
    pref_titolo_studio         VARCHAR(50),
    pref_corporatura           VARCHAR(30),
    pref_fumo                  BOOLEAN,
    pref_alcol                 BOOLEAN,
    pref_fede_religiosa        VARCHAR(50),
    pref_importanza_religione  SMALLINT
);

-- ------------------------------------------------------------
-- §7.5 Test e scoring psicometrico + EQ + attaccamento — v.
-- Ainima_00_Indice_Schema_Consolidato_v1.md §4.4-4.8 (v2): niente più
-- chat-intervista LLM, tutti e 3 i test (Big Five, Attaccamento, EQ)
-- sono questionari scritti a scoring deterministico. attaccamento_probabilita/
-- red_flags_rilevati/incongruenze_test_intervista/transcript_id/
-- chat_transcript/chat_eq_completata_il/richiede_revisione_umana RIMOSSI:
-- erano output del rubric-scorer su conversazione libera, ora eliminato
-- per motivi di sicurezza (superficie di prompt injection su dati
-- sensibili) — v. CLAUDE.md.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS psychometric_scores (
    user_id                          UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    score_big5_estroversione         REAL,
    score_big5_gradevolezza          REAL,
    score_big5_coscienziosita        REAL,
    score_big5_nevroticismo          REAL,
    score_big5_apertura              REAL,
    -- Ainima_Test_Attaccamento_v1.md: 2 dimensioni continue (dato primario),
    -- ECR-R-like, sostituiscono la distribuzione a 4 stili dedotta da LLM.
    ansia_score                      REAL,
    evitamento_score                 REAL,
    -- derivato per sole finalità di UI dalle soglie deterministiche di
    -- Ainima_Test_Attaccamento_v1.md §5 Step 4 — mai usato nel calcolo di
    -- matching, che lavora sempre sulle due dimensioni continue sopra.
    stile_attaccamento               VARCHAR(30),
    -- Ainima_Test_EQScore_v1.md: 4 pilastri da questionario scritto (32 item),
    -- non più dal rubric-scorer LLM.
    eq_pilastro_autoconsapevolezza   REAL,
    eq_pilastro_autoregolazione      REAL,
    eq_pilastro_empatia              REAL,
    eq_pilastro_responsabilita       REAL,
    score_maturita_emotiva           REAL,
    -- true se: (a) incoerenza statistica Big Five/EQ (Ainima_Test_EQScore_v1.md
    -- §4, confronto puramente numerico tra due test già raccolti, zero LLM)
    -- oppure (b) quadrante Timoroso/Disorganizzato dell'attaccamento
    -- (ansia_score > 0.7 E evitamento_score > 0.7 — Algoritmo_Ranking_Finale §10).
    -- Segnala il PROFILO per revisione dati/cura della persona, non è un
    -- giudizio sull'utente, esclude dal matching automatico finché non
    -- revisionato da uno staff (v. matching_engine.hard_filters_ok).
    flag_profilo_per_revisione_dati  BOOLEAN NOT NULL DEFAULT FALSE,
    -- Domande trappola condivise (Ainima_00_Indice_Schema_Consolidato_v1.md,
    -- sezione dedicata): 1 item di attenzione dentro ciascuno dei 3 test
    -- Likert (Big Five/Attaccamento/EQ), indipendente da qualunque
    -- dimensione. Contatore cumulativo su un massimo di 3 (uno per test) —
    -- SE >= 1: flag_profilo_per_revisione_dati = true (soglia più bassa
    -- degli altri meccanismi di confidenza, l'istruzione qui è esplicita).
    flag_trappola_fallita            SMALLINT NOT NULL DEFAULT 0,
    self_profile_canonico            TEXT,
    ideal_partner_profile_canonico   TEXT,
    self_embedding_vector            DOUBLE PRECISION[],  -- v. nota pgvector in cima al file
    ideal_embedding_vector           DOUBLE PRECISION[],
    report_prontezza_relazionale     TEXT
);

-- ------------------------------------------------------------
-- §7.5b Campi descrittivi liberi (RF-07b) — Ainima_00_Indice_Schema_
-- Consolidato_v1.md §4.2. Alimentano ESCLUSIVAMENTE Prompt 3a/3b
-- (estrazione profilo canonico, trasformazione singola non conversazionale)
-- e mai direttamente lo score di compatibilità (RNF-11) — v. CLAUDE.md.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profile_narrative (
    user_id                     UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    descrizione_di_se           TEXT,
    descrizione_partner_ideale  TEXT,
    data_ultima_modifica        TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- Liste "Mi Piace/Non Sopporto" (Ainima_Liste_Piace_Detesta_v1.md) —
-- tabella SEPARATA da profile_narrative apposta: a differenza dei due
-- campi liberi sopra (che alimentano solo il report, mai lo score, per
-- RNF-11), queste 4 liste ENTRANO DAVVERO nel FINAL_SCORE
-- (Punteggio_Tag_Liste dentro lo STEP 4 — Preferenze Soft), quindi non
-- vanno confuse con lo stesso vincolo di isolamento.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interest_tags (
    user_id                   UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    mi_piace                  TEXT,  -- input grezzo, lista separata da virgola
    non_sopporto               TEXT,
    partner_vorrei              TEXT,
    partner_non_vorrei           TEXT,
    mi_piace_tags                TEXT[],  -- dopo parsing/normalizzazione (trim/lowercase/dedup)
    non_sopporto_tags             TEXT[],
    partner_vorrei_tags            TEXT[],
    partner_non_vorrei_tags         TEXT[],
    data_ultima_modifica              TIMESTAMPTZ
);

-- Cache condivisa tra TUTTI gli utenti (non per-utente) — un tag mai
-- visto viene incorporato una sola volta e riusato da chiunque scriva
-- lo stesso tag in futuro. Cresce lentamente: i tag comuni si esauriscono
-- presto (v. Ainima_Liste_Piace_Detesta_v1.md §2).
CREATE TABLE IF NOT EXISTS tag_embedding_cache (
    tag_normalizzato       VARCHAR(120) PRIMARY KEY,
    embedding_vector         DOUBLE PRECISION[] NOT NULL,  -- v. nota pgvector in cima al file
    -- Nome del modello che ha prodotto il vettore (v. text_embedding.MODELLO_
    -- EMBEDDING). Una cache che non scade mai è a rischio se Google cambia
    -- silenziosamente il comportamento del modello (già successo in questo
    -- progetto con i modelli generativi Gemini, v. CLAUDE.md) — senza questa
    -- colonna, vettori pre/post cambiamento finirebbero mescolati nella
    -- stessa cache senza modo di accorgersene.
    modello_embedding       VARCHAR(60) NOT NULL,
    prima_volta_vista_il        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Correzione anisotropia (2026-08-20, v. CLAUDE.md): gli embedding di
-- gemini-embedding-001 su testo cortissimo (singole parole/frasi brevi come
-- questi tag) hanno una similarità coseno di base anomala anche fra
-- concetti scollegati (~0.6, verificato anche fra due non-parole senza
-- significato) — un problema geometrico dello spazio vettoriale, non
-- semantico. Sottrarre il vettore medio (centroide) calcolato su un
-- campione di tag prima del confronto corregge in modo netto la
-- separazione (verificato: sinonimi/scollegati che erano quasi
-- indistinguibili tornano ben separati). Riga singola (id=1), ricalcolata
-- manualmente via scripts/ricalcola_centroide_tag.py — nessuno scheduler
-- reale, stesso limite già accettato altrove nel progetto (v. CLAUDE.md).
CREATE TABLE IF NOT EXISTS tag_embedding_centroide (
    id                     SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    vettore                DOUBLE PRECISION[] NOT NULL,
    numero_tag_campione    INTEGER NOT NULL,
    calcolato_il           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- §7.6 Abbinamenti
-- ------------------------------------------------------------

-- Versioning dell'algoritmo di matching: la LOGICA (quale codice/approccio,
-- es. ciclo greedy vs abbinamento stabile) cambia raramente e va descritta
-- qui a parole; i PARAMETRI (pesi, soglie) possono cambiare via
-- system_config anche senza toccare il codice — per questo matches ha
-- entrambi i riferimenti separati, servono tutti e due per ricostruire
-- davvero perché un abbinamento è stato fatto, anche a distanza di anni.
CREATE TABLE IF NOT EXISTS matching_algorithm_versions (
    versione            VARCHAR(50) PRIMARY KEY,
    data_introduzione    TIMESTAMPTZ NOT NULL DEFAULT now(),
    descrizione           TEXT NOT NULL
);

INSERT INTO matching_algorithm_versions (versione, descrizione) VALUES
    ('stable_v1', 'Abbinamento stabile generalizzato (propose-and-hold, variante non bipartita di Gale-Shapley) su STEP 0-4 + tie-break visivo bidirezionale con soglia minima diretta sulla somiglianza (no controllo di coerenza di genere). Filtro storico pre-lista: esclude coppie già proposte negli ultimi system_config.mesi_esclusione_rimatch mesi. Sostituisce il ciclo greedy iniziale (ordine fisso per source_actor_id, senza reciprocità). Coerenza Narrativa (STEP 3) a placeholder neutro 0.5, pipeline LLM non ancora costruita.'),
    ('stable_v2', 'Come stable_v1, con la distanza non più un tetto fisso in km ma un fattore condizionale su importanza_vicinanza_geografica + lingue_parlate oltre la soglia urbana (Ainima_Algoritmo_Ranking_Finale_v1.md §3bis).'),
    ('stable_v3', 'Allineamento ai documenti aggiornati dopo la sessione con lo psicologo (v. CLAUDE.md): (a) attaccamento da formula continua ansia/evitamento (Ainima_Test_Attaccamento_v1.md) invece della matrice 4x4 su etichette dedotte da LLM; (b) Coerenza Narrativa da similarità vettoriale pura tra self/ideal embedding (Ainima_Matching_Semantico_Report_v1.md §5), Judge LLM Prompt 4 eliminato — nessuna IA generativa nel calcolo dei punteggi (RNF-11); (c) filtro hard su flag_profilo_per_revisione_dati (incoerenze statistiche Big Five/EQ o quadrante Timoroso/Disorganizzato) al posto di red_flags_rilevati; (d) selezione per somiglianza visiva (RF-11a/RF-11b) sempre applicata sulla shortlist di dimensione_shortlist_analisi_visiva candidati per compatibilità, non più solo come tie-break tra quasi pari.'),
    ('stable_v4', 'Aggiunta Punteggio_Tag_Liste (Ainima_Liste_Piace_Detesta_v1.md) dentro lo STEP 4 — Preferenze Soft: confronto a similarità vettoriale per singolo tag (non per profilo intero) tra le liste mi_piace/non_sopporto/partner_vorrei/partner_non_vorrei di due candidati, con penalità dedicata sui rifiuti espliciti (flag_rifiuto_esplicito se > 0.7). Cache di embedding condivisa tra tutti gli utenti per tag (tag_embedding_cache), non ricalcolata ad ogni confronto.'),
    ('stable_v5', 'Ricalibrata la soglia minima del tie-break visivo RF-11a/RF-11b: da valore assoluto fisso (0.20, scelto a occhio) a valore ricalcolato sul percentile target (default 90°) della distribuzione reale di similarità ArcFace tra coppie casuali del pool corrente (system_config.soglia_similarita_visiva_minima/soglia_percentile_similarita_visiva). Trovato durante un test di matching reale che 0.20 era sotto il 66° percentile delle coppie casuali — il tie-break scattava spesso su rumore statistico, non su somiglianza reale.')
ON CONFLICT (versione) DO NOTHING;

CREATE TABLE IF NOT EXISTS matches (
    match_id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a_id                         UUID NOT NULL REFERENCES users(user_id),
    user_b_id                         UUID NOT NULL REFERENCES users(user_id),
    stato                             stato_match_enum NOT NULL DEFAULT 'Proposto',
    final_score                       REAL,
    data_proposta                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_scadenza_risposta            TIMESTAMPTZ,
    pagamento_a_stato                 VARCHAR(20),
    pagamento_b_stato                 VARCHAR(20),
    data_conferma                     TIMESTAMPTZ,
    contatto_scambiato                BOOLEAN NOT NULL DEFAULT FALSE,
    shortlist_candidati                UUID[],
    -- v. RF-11a/RF-11b: true se il vincitore finale non è il primo per
    -- punteggio caratteriale puro nella shortlist, cioè se la somiglianza
    -- visiva ha davvero cambiato la scelta rispetto al solo FINAL_SCORE
    -- (stable_v3 — v. CLAUDE.md; prima del 2026-08-19 indicava un tie-break
    -- tra candidati quasi pari, non più il comportamento attuale)
    selezionato_per_somiglianza_visiva BOOLEAN NOT NULL DEFAULT FALSE,
    -- versioning: v. tabella matching_algorithm_versions sopra
    algoritmo_versione                 VARCHAR(50) REFERENCES matching_algorithm_versions(versione),
    algoritmo_parametri                 JSONB, -- snapshot dei pesi/soglie da system_config usati per QUESTO abbinamento
    CONSTRAINT chk_users_diversi CHECK (user_a_id <> user_b_id)
);

-- ------------------------------------------------------------
-- §7.7 Feedback
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_feedback (
    match_id             UUID NOT NULL REFERENCES matches(match_id),
    user_id               UUID NOT NULL REFERENCES users(user_id),
    data_richiesta         TIMESTAMPTZ,
    data_risposta           TIMESTAMPTZ,
    esito                  VARCHAR(50),
    note_libere             TEXT,
    usato_per_ritaratura    BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (match_id, user_id)
);

-- ------------------------------------------------------------
-- §7.9 Moderazione contenuti (RF-06b/RF-25c) — nessun provider ancora
-- collegato (v. CLAUDE.md), tabella pronta per quando verrà scelto.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_moderation_log (
    moderation_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    tipo_immagine           VARCHAR(20) NOT NULL, -- 'Foto profilo' | 'Foto partner ideale'
    immagine_url             VARCHAR(255) NOT NULL,
    esito_automatico          VARCHAR(15) NOT NULL DEFAULT 'In errore', -- 'OK' | 'Sospetta' | 'In errore'
    score_confidenza          REAL,
    data_scansione             TIMESTAMPTZ NOT NULL DEFAULT now(),
    esito_revisione_umana      VARCHAR(15) NOT NULL DEFAULT 'In attesa', -- 'In attesa' | 'Approvato' | 'Rifiutato'
    revisionato_da              UUID,
    data_revisione               TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- §7.10 Richieste di recupero accesso / cambio email (RF-26/26b/26c/26d)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_change_requests (
    request_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                       UUID REFERENCES users(user_id) ON DELETE CASCADE, -- nullo se non ancora identificato
    email_attuale_dichiarata       VARCHAR(255),
    email_nuova_richiesta           VARCHAR(255) NOT NULL,
    dati_identificativi_forniti      JSONB, -- {nome, cognome, data_nascita, citta, ultime4cifre_carta}
    origine                          VARCHAR(40) NOT NULL, -- 'Self-service da account autenticato' | 'Modulo pubblico recupero accesso'
    stato                            VARCHAR(25) NOT NULL DEFAULT 'In attesa revisione',
    -- 'In attesa revisione' | 'Approvata' | 'Rifiutata' | 'In periodo di grazia' | 'Completata' | 'Annullata'
    revisionato_da                    UUID, -- nullo per il self-service (RF-26, nessuna revisione umana necessaria)
    data_richiesta                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_decisione                      TIMESTAMPTZ,
    data_scadenza_grazia                 TIMESTAMPTZ,
    token_annullamento                    VARCHAR(255) -- per il link "annulla" inviato alla vecchia email (RF-26d)
);

-- ------------------------------------------------------------
-- §7.8 Parametri di configurazione (admin console)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_config (
    chiave              VARCHAR(80) PRIMARY KEY,
    valore               VARCHAR(255) NOT NULL,
    descrizione           TEXT,
    data_ultima_modifica  TIMESTAMPTZ NOT NULL DEFAULT now(),
    modificato_da         UUID
);

INSERT INTO system_config (chiave, valore, descrizione) VALUES
    -- Rinominato da matching_stage2_pool_size (Judge LLM Stage 2, eliminato
    -- — v. Ainima_Matching_Semantico_Report_v1.md §5): il ranking è ora puro
    -- calcolo vettoriale su tutto il pool, questo parametro regola solo
    -- quanti report testuali (Prompt 5) pre-generare, non i punteggi.
    ('report_top_candidates',         '10',   'Numero di candidati migliori per cui pre-generare un report testuale (Prompt 5) — non influenza il calcolo dei punteggi'),
    -- RF-11a/RF-25b: dimensione della shortlist per carattere da cui, se
    -- l'utente ha caricato la foto "partner ideale", si sceglie SEMPRE il
    -- candidato visivamente più simile (v. decisione utente, sostituisce il
    -- tie-break-solo-tra-quasi-pari deciso il 12/08 — v. CLAUDE.md).
    ('dimensione_shortlist_analisi_visiva', '5', 'Numero di candidati Top N per compatibilità caratteriale tra cui scegliere per somiglianza visiva (RF-11a/RF-11b), se la foto "partner ideale" è presente'),
    -- stable_v5 (v. CLAUDE.md — test di matching reale Pietro/Lena Gallo):
    -- 0.20 era un valore assoluto scelto a occhio — verificato che il 90°
    -- percentile della similarità ArcFace tra coppie CASUALI del pool era
    -- già 0.334, quindi la vecchia soglia faceva scattare il tie-break
    -- visivo anche su puro rumore statistico. soglia_similarita_visiva_minima
    -- è il valore CALCOLATO (scripts/ricalcola_soglia_visiva.py, nessuno
    -- scheduler reale, va rilanciato periodicamente) sul percentile target
    -- soglia_percentile_similarita_visiva della distribuzione reale corrente.
    ('soglia_percentile_similarita_visiva', '0.90', 'Percentile target (0-1) della distribuzione di similarità ArcFace tra coppie casuali del pool, usato per ricalcolare soglia_similarita_visiva_minima'),
    ('soglia_similarita_visiva_minima', '0.20', 'Soglia minima di somiglianza visiva (RF-11a/RF-11b) sotto cui il tie-break non scatta — valore CALCOLATO da scripts/ricalcola_soglia_visiva.py sul percentile target sopra, non un default da editare a mano'),
    ('weight_bigfive',                 '0.30', 'Peso w1 Big Five nel FINAL_SCORE'),
    ('weight_eq_attaccamento',         '0.35', 'Peso w2 EQ/Attaccamento nel FINAL_SCORE'),
    ('weight_narrativa',               '0.20', 'Peso w3 Coerenza Narrativa (similarità vettoriale, non più LLM) nel FINAL_SCORE'),
    ('weight_preferenze_soft',         '0.15', 'Peso w4 Preferenze Soft nel FINAL_SCORE'),
    ('weight_eq_autoconsapevolezza',   '0.25', 'Peso del pilastro Autoconsapevolezza in score_maturita_emotiva (Ainima_Test_EQScore_v1.md)'),
    ('weight_eq_autoregolazione',      '0.25', 'Peso del pilastro Autoregolazione in score_maturita_emotiva'),
    ('weight_eq_empatia',              '0.25', 'Peso del pilastro Empatia in score_maturita_emotiva'),
    ('weight_eq_responsabilita',       '0.25', 'Peso del pilastro Responsabilità relazionale in score_maturita_emotiva'),
    ('soglia_minima_proposta',         '0.55', 'Sotto questa soglia nessuna proposta viene generata quel mese (Slow Matching)'),
    ('fee_match_confermato_eur',       '15',   'Fee addebitata a ciascun utente alla conferma reciproca del match (v. decisione in CLAUDE.md)'),
    ('recupero_accesso_grazia_ore',    '48',   'Ore del periodo di grazia dopo l''approvazione di un cambio email, entro cui la vecchia email può annullare (RF-26d)'),
    ('finestra_risposta_match_giorni', '7',    'Giorni entro cui entrambe le parti devono accettare la proposta'),
    ('mesi_esclusione_rimatch',        '6',    'Una coppia già proposta negli ultimi N mesi non viene riproposta — non è una esclusione permanente (v. decisione in CLAUDE.md sullo stable matching)'),
    ('giorno_esecuzione_ciclo_mensile', '1',   'Giorno del mese in cui gira il ciclo di matching mensile (RF-11) — usato per mostrare agli utenti la prossima data prevista di proposta'),
    ('soglia_area_urbana_km',           '50',  'Sotto questa soglia la distanza resta un filtro/punteggio graduato "classico"; oltre, entra la logica basata su importanza_vicinanza_geografica + lingue_parlate (Algoritmo_Ranking_Finale §3bis)'),
    ('soglia_importanza_vicinanza_esclusione', '0.6', 'Sopra questo valore medio tra i due profili (oltre la soglia urbana), la distanza torna a essere un filtro escludente (Algoritmo_Ranking_Finale §3bis/§9)'),
    ('otp_scadenza_minuti',             '10',  'Minuti di validità di un codice OTP email prima che scada (RF-02)'),
    ('otp_tentativi_massimi',           '5',   'Tentativi di verifica falliti consentiti prima di dover richiedere un nuovo codice OTP'),
    ('otp_richiesta_cooldown_secondi',  '60',  'Secondi minimi tra due richieste di OTP per la stessa email, anti-abuso'),
    ('otp_rate_limit_ip_per_ora',       '10',  'Numero massimo di richieste OTP consentite dallo stesso IP in un''ora, anti-abuso'),
    ('jwt_scadenza_giorni',             '30',  'Giorni di validità del token di sessione emesso alla verifica OTP (v. CLAUDE.md: emesso ma non ancora applicato su altre rotte)')
ON CONFLICT (chiave) DO NOTHING;
