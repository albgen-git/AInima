import type { Genere, Orientamento, SiNoDaValutare, SiNoIndifferente } from "@/lib/api";

export interface WizardState {
  userId: string | null;

  // Step: email — unico punto d'ingresso, per utenti nuovi e di ritorno
  // (RF-02, autenticazione via OTP, niente password — v. CLAUDE.md)
  email: string;

  // Step: verifica OTP
  otpInviato: boolean;

  // Step: info di base (raccolte DOPO la verifica OTP: l'account esiste
  // già con la sola email a questo punto)
  nome: string;
  cognome: string;
  data_nascita: string;
  genere: Genere | "";
  // autodichiarato, mai verificato in questa fase (RF-02b)
  telefono: string;

  // Step: consenso dati sensibili (art. 9 GDPR)
  consensoDatiSensibili: boolean;

  // Step: orientamento sessuale — dato particolare, raccolto solo dopo il
  // consenso esplicito (v. CLAUDE.md).
  orientamento_sessuale: Orientamento | "";

  // Step: pagamento
  cartaRegistrata: boolean;

  // Step: stato civile
  stato_civile: string;
  ha_figli: boolean | null;

  // Step: profilo fisico/socio-economico
  altezza_cm: string;
  peso_kg: string;
  corporatura: string;
  colore_capelli: string;
  colore_occhi: string;
  fumo: boolean | null;
  alcol: boolean | null;
  stile_vita_sport: string;
  comune_residenza: string;
  titolo_studio: string;
  settore_occupazionale: string;
  fascia_reddito: string;
  fede_religiosa: string;
  importanza_religione: string;

  // Step: foto
  foto_profilo_url: string | null;
  foto_partner_ideale_url: string | null;

  // Step: criteri dealbreaker
  pref_genere_cercato: Genere | "";
  pref_eta_min: string;
  pref_eta_max: string;
  pref_accetta_figli: SiNoIndifferente;
  pref_desidera_figli_futuri: SiNoDaValutare;
  // Sostituiscono pref_distanza_max_km (superato) — v. CLAUDE.md.
  importanza_vicinanza_geografica: string;
  lingue_parlate: string;

  // Step: criteri soft
  pref_altezza_min: string;
  pref_altezza_max: string;
  pref_stato_civile_accettato: string;
  pref_titolo_studio: string;
  pref_corporatura: string;
  pref_fumo: boolean | null;
  pref_alcol: boolean | null;
  pref_fede_religiosa: string;
  pref_importanza_religione: string;

  // Step: Big Five
  bigFiveCompletato: boolean;

  // Step: test Attaccamento (24 item, sostituisce la chat EQ — v. CLAUDE.md)
  attaccamentoCompletato: boolean;

  // Step: test EQ Score (32 item, sostituisce la chat EQ — v. CLAUDE.md)
  eqCompletato: boolean;

  // Step: Test Profilo Relazionale (26 item, Blocco D — v. CLAUDE.md,
  // Ainima_Test_Profilo_Relazionale_v1.md) — sostituisce il confronto a
  // embedding nel calcolo di matching, entra nel gate di attivazione RF-09
  // al pari di Big Five/Attaccamento/EQ.
  profiloRelazionaleCompletato: boolean;

  // Step: campi liberi RF-07b (sostituiscono la chat EQ — v. CLAUDE.md)
  descrizione_di_se: string;
  descrizione_partner_ideale: string;

  // Step: liste "mi piace/non sopporto" RF-08c (v. CLAUDE.md,
  // Ainima_Liste_Piace_Detesta_v1.md) — a differenza dei due campi sopra,
  // queste ENTRANO nel calcolo del match, non solo nel report.
  mi_piace: string;
  non_sopporto: string;
  partner_vorrei: string;
  partner_non_vorrei: string;

  // Step: chat EQ — DISATTIVATO lato backend, non più nel wizard attivo,
  // campo tenuto solo perché StepInterview.tsx non è stato cancellato.
  chatCompletata: boolean;
}

export const initialWizardState: WizardState = {
  userId: null,
  email: "",
  otpInviato: false,
  nome: "",
  cognome: "",
  data_nascita: "",
  genere: "",
  telefono: "",
  consensoDatiSensibili: false,
  orientamento_sessuale: "",
  cartaRegistrata: false,
  stato_civile: "",
  ha_figli: null,
  altezza_cm: "",
  peso_kg: "",
  corporatura: "",
  colore_capelli: "",
  colore_occhi: "",
  fumo: null,
  alcol: null,
  stile_vita_sport: "",
  comune_residenza: "",
  titolo_studio: "",
  settore_occupazionale: "",
  fascia_reddito: "",
  fede_religiosa: "",
  importanza_religione: "",
  foto_profilo_url: null,
  foto_partner_ideale_url: null,
  pref_genere_cercato: "",
  pref_eta_min: "25",
  pref_eta_max: "45",
  pref_accetta_figli: "Indifferente",
  pref_desidera_figli_futuri: "Da valutare",
  importanza_vicinanza_geografica: "3",
  lingue_parlate: "",
  pref_altezza_min: "",
  pref_altezza_max: "",
  pref_stato_civile_accettato: "",
  pref_titolo_studio: "",
  pref_corporatura: "",
  pref_fumo: null,
  pref_alcol: null,
  pref_fede_religiosa: "",
  pref_importanza_religione: "",
  bigFiveCompletato: false,
  attaccamentoCompletato: false,
  eqCompletato: false,
  profiloRelazionaleCompletato: false,
  descrizione_di_se: "",
  descrizione_partner_ideale: "",
  mi_piace: "",
  non_sopporto: "",
  partner_vorrei: "",
  partner_non_vorrei: "",
  chatCompletata: false,
};

export type WizardUpdater = <K extends keyof WizardState>(
  key: K,
  value: WizardState[K]
) => void;

export interface StepProps {
  state: WizardState;
  update: WizardUpdater;
  onNext: () => void;
  onBack: () => void;
}
