import { apiAssetUrl } from "./client";

export * from "./types";
export { apiClient, apiAssetUrl, ApiError, NetworkError, API_BASE_URL } from "./client";
export { authApi } from "./auth";
export { profileApi } from "./profile";
export { preferencesApi } from "./preferences";
export { psychometricApi } from "./psychometric";
export { matchingApi } from "./matching";
export { paymentsApi } from "./payments";
export { contactsApi } from "./contacts";
export { feedbackApi } from "./feedback";
export { engagementApi } from "./engagement";
export { personalReportApi } from "./personalReport";

/**
 * URL assoluto per mostrare una foto. `foto_profilo_url`/`foto_partner_ideale_url`
 * sono un path relativo allo storage locale del backend (servito da /photos/,
 * v. backend/main.py) per i profili caricati prima della migrazione a R2, ma
 * un URL già assoluto (https://pub-....r2.dev/...) per quelli su R2 (v.
 * backend/services/photo_storage.py) — senza questa distinzione si otterrebbe
 * un URL rotto tipo "/photos/https://pub-..." (stesso bug già trovato e
 * corretto nel viewer admin lato backend, v. CLAUDE.md).
 */
export function photoUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return apiAssetUrl(`/photos/${path}`);
}
