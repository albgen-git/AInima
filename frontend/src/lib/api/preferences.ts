import { apiClient } from "./client";
import type {
  DealbreakerCriteriaIn,
  InterestTagsUpdate,
  InterestTagsUpdateResponse,
  PreferencesOut,
  SoftCriteriaIn,
} from "./types";

export const preferencesApi = {
  getPreferences: (userId: string) =>
    apiClient.get<PreferencesOut>(`/users/${userId}/preferences`),

  updateDealbreaker: (userId: string, payload: DealbreakerCriteriaIn) =>
    apiClient.put<{ aggiornato: boolean }>(
      `/users/${userId}/preferences/dealbreaker`,
      payload
    ),

  updateSoft: (userId: string, payload: SoftCriteriaIn) =>
    apiClient.put<{ aggiornato: boolean }>(
      `/users/${userId}/preferences/soft`,
      payload
    ),

  /** RF-08c — liste "mi piace/non sopporto", v. Ainima_Liste_Piace_Detesta_v1.md. */
  updateInterestTags: (userId: string, payload: InterestTagsUpdate) =>
    apiClient.put<InterestTagsUpdateResponse>(
      `/users/${userId}/preferences/tags`,
      payload
    ),
};
