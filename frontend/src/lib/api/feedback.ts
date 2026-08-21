import { apiClient } from "./client";
import type { FeedbackIn, FeedbackResponse } from "./types";

export const feedbackApi = {
  submitFeedback: (userId: string, matchId: string, payload: FeedbackIn) =>
    apiClient.post<FeedbackResponse>(
      `/users/${userId}/matches/${matchId}/feedback`,
      payload
    ),
};
