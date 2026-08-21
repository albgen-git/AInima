/**
 * Tipi TS allineati agli schemi Pydantic del backend (backend/schemas/*.py).
 * I nomi dei campi restano in italiano, identici alla risposta reale
 * dell'API — nessuna traduzione qui, solo tipizzazione.
 */

export type Genere = "Maschile" | "Femminile" | "Non binario" | "Altro";

export type Orientamento =
  | "Eterosessuale"
  | "Omosessuale"
  | "Bisessuale"
  | "Pansessuale"
  | "Asessuale"
  | "Altro";

export type StatoAccount = "In attesa" | "Attivo" | "Sospeso" | "Chiuso";

export type StatoMatch =
  | "Proposto"
  | "Accettato_A"
  | "Accettato_B"
  | "Confermato"
  | "Rifiutato"
  | "Scaduto";

export type SiNoIndifferente = "Si" | "No" | "Indifferente";
export type SiNoDaValutare = "Si" | "No" | "Da valutare";

// ── auth.py ────────────────────────────────────────────────────────────

// Autenticazione via email OTP (RF-02, niente password permanente) —
// v. CLAUDE.md per la cronologia del passaggio da email+password a OTP.
export interface RequestOtpRequest {
  email: string;
}

export interface RequestOtpResponse {
  inviato: boolean;
}

export interface VerifyOtpRequest {
  email: string;
  codice: string;
}

export interface VerifyOtpResponse {
  user_id: string;
  stato_account: StatoAccount;
  /** Emesso ma non ancora richiesto su altre rotte — v. CLAUDE.md. */
  token: string;
}

export interface PaymentMethodRequest {
  metodo_pagamento_token: string;
}

export interface PaymentMethodResponse {
  pre_autorizzato: boolean;
  nota: string;
}

export interface OnboardingChecklist {
  email_verificata: boolean;
  carta_registrata: boolean;
  profilo_fisico_compilato: boolean;
  test_bigfive_completato: boolean;
}

export interface OnboardingStatus {
  stato_account: StatoAccount;
  checklist: OnboardingChecklist;
  onboarding_completo: boolean;
  /** Indice (0-9) del primo step del wizard onboarding non ancora completato — v. backend/routers/auth.py STEP_*. */
  primo_passo_incompleto: number;
}

export interface DashboardOut {
  stato_account: StatoAccount;
  livello_abbonamento: string | null;
  data_scadenza_abbonamento: string | null;
  prossima_data_ciclo: string | null; // solo se stato_account === "Attivo"
  ha_proposta_attiva: boolean;
}

// ── profile.py ─────────────────────────────────────────────────────────

export interface ProfileOut {
  nome: string | null;
  cognome: string | null;
  data_nascita: string | null;
  genere: Genere | null;
  orientamento_sessuale: Orientamento | null;
  telefono: string | null;
  email: string;
  email_verificata: boolean;
  stato_civile: string | null;
  ha_figli: boolean | null;
  altezza_cm: number | null;
  peso_kg: number | null;
  corporatura: string | null;
  colore_capelli: string | null;
  colore_occhi: string | null;
  fumo: boolean | null;
  alcol: boolean | null;
  stile_vita_sport: string | null;
  foto_profilo_url: string | null;
  foto_partner_ideale_url: string | null;
  comune_residenza: string | null;
  titolo_studio: string | null;
  settore_occupazionale: string | null;
  fascia_reddito: string | null;
  fede_religiosa: string | null;
  importanza_religione: number | null;
  /** Sostituisce pref_distanza_max_km (superato) — v. Ainima_Algoritmo_Ranking_Finale_v1.md §3bis. */
  importanza_vicinanza_geografica: number | null;
  lingue_parlate: string[] | null;
}

export interface ProfileUpdate {
  nome?: string | null;
  cognome?: string | null;
  data_nascita?: string | null;
  genere?: Genere | null;
  /** Autodichiarato, mai verificato in questa fase (RF-02b). */
  telefono?: string | null;
  /** Dato particolare ex art. 9 GDPR — inviare solo dopo lo step di consenso esplicito. */
  orientamento_sessuale?: Orientamento | null;
  /** Deve essere true se inviato — il backend rifiuta un false esplicito. */
  consenso_dati_sensibili?: boolean;
  altezza_cm?: number | null;
  peso_kg?: number | null;
  corporatura?: string | null;
  colore_capelli?: string | null;
  colore_occhi?: string | null;
  fumo?: boolean | null;
  alcol?: boolean | null;
  stile_vita_sport?: string | null;
  comune_residenza?: string | null;
  lat?: number | null;
  lon?: number | null;
  titolo_studio?: string | null;
  settore_occupazionale?: string | null;
  fascia_reddito?: string | null;
  fede_religiosa?: string | null;
  importanza_religione?: number | null;
  stato_civile?: string | null;
  ha_figli?: boolean | null;
  /** Likert 1-5 grezzo — normalizzato 0.0-1.0 lato server (v. ProfileOut, che invece riporta già il valore normalizzato). */
  importanza_vicinanza_geografica?: number | null;
  lingue_parlate?: string[] | null;
}

export interface ProfilePhotoResponse {
  foto_profilo_url: string;
  embedding_calcolato: false;
}

export interface IdealPartnerPhotoResponse {
  foto_partner_ideale_url: string;
  embedding_calcolato: false;
}

// ── preferences.py ─────────────────────────────────────────────────────

export interface DealbreakerCriteriaOut {
  user_id: string;
  pref_genere_cercato: Genere | null;
  pref_eta_min: number;
  pref_eta_max: number;
  pref_accetta_figli: SiNoIndifferente;
  pref_desidera_figli_futuri: SiNoDaValutare;
}

export interface SoftCriteriaOut {
  user_id: string;
  pref_altezza_min: number | null;
  pref_altezza_max: number | null;
  pref_stato_civile_accettato: string | null;
  pref_titolo_studio: string | null;
  pref_corporatura: string | null;
  pref_fumo: boolean | null;
  pref_alcol: boolean | null;
  pref_fede_religiosa: string | null;
  pref_importanza_religione: number | null;
}

export interface PreferencesOut {
  dealbreaker: DealbreakerCriteriaOut | null;
  soft: SoftCriteriaOut | null;
}

export interface DealbreakerCriteriaIn {
  pref_genere_cercato?: Genere | null;
  pref_eta_min: number;
  pref_eta_max: number;
  pref_accetta_figli: SiNoIndifferente;
  pref_desidera_figli_futuri: SiNoDaValutare;
}

export interface SoftCriteriaIn {
  pref_altezza_min?: number | null;
  pref_altezza_max?: number | null;
  pref_stato_civile_accettato?: string | null;
  pref_titolo_studio?: string | null;
  pref_corporatura?: string | null;
  pref_fumo?: boolean | null;
  pref_alcol?: boolean | null;
  pref_fede_religiosa?: string | null;
  pref_importanza_religione?: number | null;
}

// RF-08c — liste "mi piace/non sopporto", v. Ainima_Liste_Piace_Detesta_v1.md.
// A differenza dei campi liberi narrativi, ENTRANO nel calcolo del match
// (Punteggio_Tag_Liste, STEP 4) — v. CLAUDE.md.
export interface InterestTagsUpdate {
  mi_piace?: string | null;
  non_sopporto?: string | null;
  partner_vorrei?: string | null;
  partner_non_vorrei?: string | null;
}

export interface InterestTagsUpdateResponse {
  aggiornato: boolean;
  mi_piace_tags?: string[];
  non_sopporto_tags?: string[];
  partner_vorrei_tags?: string[];
  partner_non_vorrei_tags?: string[];
}

// ── psychometric.py ────────────────────────────────────────────────────

export interface BigFiveSubmission {
  risposte: Record<string, number>; // 50 chiavi: E1-10, A1-10, C1-10, N1-10, O1-10, valori 1-5
}

export interface BigFiveResult {
  score_big5_estroversione: number;
  score_big5_gradevolezza: number;
  score_big5_coscienziosita: number;
  score_big5_nevroticismo: number;
  score_big5_apertura: number;
}

export interface AttaccamentoSubmission {
  risposte: Record<string, number>; // 24 chiavi: AN1-12, EV1-12, valori 1-5
}

export interface AttaccamentoResult {
  ansia_score: number;
  evitamento_score: number;
  stile_attaccamento: string; // solo per la UI, mai per il calcolo (v. CLAUDE.md)
}

export interface EqSubmission {
  risposte: Record<string, number>; // 32 chiavi: AC1-8, AR1-8, EM1-8, RE1-8, valori 1-5
}

export interface EqResult {
  eq_pilastro_autoconsapevolezza: number;
  eq_pilastro_autoregolazione: number;
  eq_pilastro_empatia: number;
  eq_pilastro_responsabilita: number;
  score_maturita_emotiva: number;
}

export interface NarrativeUpdate {
  descrizione_di_se?: string | null;
  descrizione_partner_ideale?: string | null;
}

/** Chat-intervista EQ — DISATTIVATA lato backend (v. CLAUDE.md 2026-08-19),
 * tipi tenuti solo perché StepInterview.tsx non è stato cancellato. */
export interface ChatMessageIn {
  testo?: string | null;
}

export interface ChatMessageOut {
  testo: string;
  conversazione_completata: boolean;
}

export interface ReportOut {
  pronto: boolean;
  testo: string | null;
}

// ── matching.py ────────────────────────────────────────────────────────

export interface ProposalOut {
  match_id: string;
  stato: StatoMatch;
  eta: number;
  genere: string;
  corporatura: string | null;
  titolo_studio: string | null;
  foto_profilo_url: string | null;
  distanza_km: number | null;
  data_scadenza_risposta: string | null;
  /** true se questo utente deve ancora rispondere — v. nota in backend/schemas/matching.py. */
  in_attesa_di_te: boolean;
}

export interface MatchDecision {
  accetta: boolean;
}

export interface MatchDecisionResponse {
  stato: StatoMatch;
  nota?: string;
}

// Coerenza narrativa — calcolo vettoriale puro (cosine similarity tra
// self/ideal embedding), non più un Judge LLM (Prompt 4, rimosso — v.
// CLAUDE.md 2026-08-19, RNF-11). Richiede other_user_id esplicito, quindi
// non utilizzabile direttamente dalla proposta anonima (v. nota in
// matching.ts).
export interface AffinityOut {
  compatibilita_narrativa_complessiva: number;
}

// GET /users/{id}/proposal/analysis — variante di AffinityOut che non
// richiede/espone mai l'ID dell'altra persona (v. lib/api/matching.ts).
export interface ProposalAnalysisOut {
  pronta: boolean;
  analisi: AffinityOut | null;
}

// ── payments.py ────────────────────────────────────────────────────────

export interface PayMatchResponse {
  pagato: boolean;
  fee_eur: string;
  nota: string;
  contatti_sbloccati: boolean;
}

// ── contacts.py ────────────────────────────────────────────────────────

export interface RubricaEntry {
  match_id: string;
  data_conferma: string | null;
  nome: string;
  cognome: string;
  foto_profilo_url: string | null;
}

// ── feedback.py ────────────────────────────────────────────────────────

export interface FeedbackIn {
  esito: string;
  note_libere?: string | null;
}

export interface FeedbackResponse {
  registrato: boolean;
}
