import { apiClient } from "./client";
import type {
  AttaccamentoResult,
  AttaccamentoSubmission,
  BigFiveResult,
  BigFiveSubmission,
  ChatMessageIn,
  ChatMessageOut,
  EqResult,
  EqSubmission,
  NarrativeUpdate,
  ProfiloRelazionaleResult,
  ProfiloRelazionaleSubmission,
  ReportOut,
} from "./types";

export const psychometricApi = {
  submitBigFive: (userId: string, payload: BigFiveSubmission) =>
    apiClient.post<BigFiveResult>(`/users/${userId}/bigfive`, payload),

  submitAttaccamento: (userId: string, payload: AttaccamentoSubmission) =>
    apiClient.post<AttaccamentoResult>(`/users/${userId}/attaccamento`, payload),

  submitEq: (userId: string, payload: EqSubmission) =>
    apiClient.post<EqResult>(`/users/${userId}/eq`, payload),

  submitProfiloRelazionale: (userId: string, payload: ProfiloRelazionaleSubmission) =>
    apiClient.post<ProfiloRelazionaleResult>(`/users/${userId}/profilo-relazionale`, payload),

  updateNarrative: (userId: string, payload: NarrativeUpdate) =>
    apiClient.put<{ aggiornato: boolean }>(`/users/${userId}/narrative`, payload),

  // Chat-intervista EQ — DISATTIVATA lato backend (v. CLAUDE.md 2026-08-19),
  // tenuta solo perché StepInterview.tsx non è stato cancellato.
  sendChatMessage: (userId: string, payload: ChatMessageIn) =>
    apiClient.post<ChatMessageOut>(`/users/${userId}/chat/message`, payload),

  getReport: (userId: string) =>
    apiClient.get<ReportOut>(`/users/${userId}/report`),
};
