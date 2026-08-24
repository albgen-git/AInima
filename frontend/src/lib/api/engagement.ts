import { apiClient } from "./client";
import type { AffinamentoItemOut, RispostaAffinamentoIn } from "./types";

export const engagementApi = {
  getDomandePendenti: (userId: string) =>
    apiClient.get<AffinamentoItemOut[]>(`/users/${userId}/affinamento/pendenti`),

  rispondiAffinamento: (userId: string, itemId: string, payload: RispostaAffinamentoIn) =>
    apiClient.post<{ registrato: boolean }>(`/users/${userId}/affinamento/${itemId}/risposta`, payload),

  segnaPillolaAperta: (userId: string, pillolaId: string) =>
    apiClient.post<{ aggiornato: boolean }>(`/users/${userId}/pillole/${pillolaId}/aperta`),
};
