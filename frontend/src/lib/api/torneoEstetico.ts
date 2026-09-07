import { apiClient } from "./client";
import type { ConfrontoIn, ConfrontoOut, PreferenzaEsteticaOut, TorneoInizio } from "./types";

export const torneoEsteticoApi = {
  inizia: (userId: string) =>
    apiClient.post<TorneoInizio>(`/users/${userId}/torneo-estetico/inizia`),

  registraConfronto: (userId: string, payload: ConfrontoIn) =>
    apiClient.post<ConfrontoOut>(`/users/${userId}/torneo-estetico/confronto`, payload),

  getPreferenza: (userId: string) =>
    apiClient.get<PreferenzaEsteticaOut>(`/users/${userId}/torneo-estetico/preferenza`),
};
