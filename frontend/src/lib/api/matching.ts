import { apiClient } from "./client";
import type {
  AffinityOut,
  MatchDecision,
  MatchDecisionResponse,
  ProposalAnalysisOut,
  ProposalOut,
} from "./types";

export const matchingApi = {
  getProposal: (userId: string) =>
    apiClient.get<ProposalOut | null>(`/users/${userId}/proposal`),

  /** Analisi caratteriale di pregi/difetti della coppia per la proposta attiva — mai espone l'altro user_id. */
  getProposalAnalysis: (userId: string) =>
    apiClient.get<ProposalAnalysisOut>(`/users/${userId}/proposal/analysis`),

  decideMatch: (userId: string, matchId: string, payload: MatchDecision) =>
    apiClient.post<MatchDecisionResponse>(
      `/users/${userId}/matches/${matchId}/decision`,
      payload
    ),

  /**
   * Coerenza narrativa (Test Profilo Relazionale, Blocco D — v. CLAUDE.md;
   * non più similarità a embedding né Judge LLM). Endpoint admin/debug,
   * mai chiamato da una pagina utente: richiede l'ID esplicito dell'altro
   * utente — GET /users/{id}/proposal NON lo espone (proposta anonima per
   * design, RF-12) — e ritorna il flag di asimmetria grezzo, non
   * riformulato (v. getProposalAnalysis sopra per la versione rivolta
   * all'utente).
   */
  getAffinity: (userId: string, otherUserId: string) =>
    apiClient.get<AffinityOut>(`/users/${userId}/affinity/${otherUserId}`),
};
