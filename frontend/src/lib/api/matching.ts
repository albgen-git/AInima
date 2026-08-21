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
   * Coerenza narrativa (similarità vettoriale, non più Judge LLM — v.
   * CLAUDE.md 2026-08-19). Richiede l'ID esplicito dell'altro utente —
   * GET /users/{id}/proposal NON lo espone (proposta anonima per design,
   * RF-12), quindi questa funzione non è collegabile alla schermata
   * "Proposta di match" (v. getProposalAnalysis sopra, che non lo richiede).
   */
  getAffinity: (userId: string, otherUserId: string) =>
    apiClient.get<AffinityOut>(`/users/${userId}/affinity/${otherUserId}`),
};
