import { apiClient } from "./client";
import type { PersonalReportFeedbackIn, PersonalReportFeedbackOut, PersonalReportOut } from "./types";

export const personalReportApi = {
  getUltimoReport: (userId: string, locale: string = "it") =>
    apiClient.get<PersonalReportOut>(`/users/${userId}/personal-report?locale=${locale}`),

  getFeedback: (userId: string, reportId: string) =>
    apiClient.get<PersonalReportFeedbackOut>(`/users/${userId}/personal-report/${reportId}/feedback`),

  inviaFeedback: (userId: string, reportId: string, payload: PersonalReportFeedbackIn) =>
    apiClient.post<{ registrato: boolean }>(`/users/${userId}/personal-report/${reportId}/feedback`, payload),
};
