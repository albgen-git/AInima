import { apiClient } from "./client";
import type { PersonalReportOut } from "./types";

export const personalReportApi = {
  getUltimoReport: (userId: string) =>
    apiClient.get<PersonalReportOut>(`/users/${userId}/personal-report`),
};
