import { apiClient } from "./client";
import type { PayMatchResponse } from "./types";

export const paymentsApi = {
  payMatch: (userId: string, matchId: string) =>
    apiClient.post<PayMatchResponse>(
      `/users/${userId}/matches/${matchId}/pay`
    ),
};
