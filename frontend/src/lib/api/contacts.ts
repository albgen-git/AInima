import { apiAssetUrl, apiClient } from "./client";
import type { RubricaEntry } from "./types";

export const contactsApi = {
  getRubrica: (userId: string) =>
    apiClient.get<RubricaEntry[]>(`/users/${userId}/rubrica`),

  /** URL diretto per il download della vCard (non JSON — apri/naviga direttamente). */
  vcardUrl: (userId: string, matchId: string) =>
    apiAssetUrl(`/users/${userId}/matches/${matchId}/vcard`),
};
