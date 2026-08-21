import { apiClient } from "./client";
import type {
  DashboardOut,
  OnboardingStatus,
  PaymentMethodRequest,
  PaymentMethodResponse,
  RequestOtpRequest,
  RequestOtpResponse,
  VerifyOtpRequest,
  VerifyOtpResponse,
} from "./types";

export const authApi = {
  requestOtp: (payload: RequestOtpRequest) =>
    apiClient.post<RequestOtpResponse>("/auth/request-otp", payload),

  verifyOtp: (payload: VerifyOtpRequest) =>
    apiClient.post<VerifyOtpResponse>("/auth/verify-otp", payload),

  setPaymentMethod: (userId: string, payload: PaymentMethodRequest) =>
    apiClient.post<PaymentMethodResponse>(
      `/auth/${userId}/payment-method`,
      payload
    ),

  getOnboardingStatus: (userId: string) =>
    apiClient.get<OnboardingStatus>(`/auth/${userId}/status`),

  getDashboard: (userId: string) =>
    apiClient.get<DashboardOut>(`/auth/${userId}/dashboard`),
};
