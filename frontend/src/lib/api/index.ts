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

/** URL assoluto per una foto servita da /photos/... (v. backend/main.py StaticFiles mount). */
export function photoUrl(relativePath: string): string {
  return apiAssetUrl(`/photos/${relativePath}`);
}
