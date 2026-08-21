import { apiClient } from "./client";
import type {
  IdealPartnerPhotoResponse,
  ProfileOut,
  ProfilePhotoResponse,
  ProfileUpdate,
} from "./types";

export const profileApi = {
  getProfile: (userId: string) =>
    apiClient.get<ProfileOut>(`/users/${userId}/profile`),

  updateProfile: (userId: string, payload: ProfileUpdate) =>
    apiClient.put<{ aggiornato: boolean }>(
      `/users/${userId}/profile`,
      payload
    ),

  uploadProfilePhoto: (userId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.postForm<ProfilePhotoResponse>(
      `/users/${userId}/profile-photo`,
      form
    );
  },

  uploadIdealPartnerPhoto: (userId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.postForm<IdealPartnerPhotoResponse>(
      `/users/${userId}/ideal-partner-photo`,
      form
    );
  },
};
