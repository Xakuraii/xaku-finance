import { api } from "@/lib/api/client";

export interface ReauthResponse {
  reauth_expires_in: number;
}

export interface TwoFactorSetupResponse {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
}

export interface TwoFactorConfirmResponse {
  enabled: boolean;
  recovery_codes: string[];
}

export interface TwoFactorVerifyResponse {
  access: string;
  user?: {
    id: string;
    email: string;
    is_email_verified: boolean;
    display_name?: string;
  };
  workspace?: {
    id: string;
    name: string;
    reporting_currency: string;
    timezone: string;
  };
}

export interface RecoveryCodesResponse {
  recovery_codes: string[];
}

export async function reauth(password: string): Promise<ReauthResponse> {
  return api.post<ReauthResponse>("/api/v1/auth/reauth/", { password });
}

export async function setupTwoFactor(): Promise<TwoFactorSetupResponse> {
  return api.post<TwoFactorSetupResponse>("/api/v1/auth/2fa/setup/");
}

export async function confirmTwoFactor(code: string): Promise<TwoFactorConfirmResponse> {
  return api.post<TwoFactorConfirmResponse>("/api/v1/auth/2fa/confirm/", { code });
}

export async function verifyTwoFactor(mfa_token: string, code: string): Promise<TwoFactorVerifyResponse> {
  return api.post<TwoFactorVerifyResponse>("/api/v1/auth/2fa/verify/", { mfa_token, code });
}

export async function disableTwoFactor(password: string, code: string): Promise<void> {
  return api.post<void>("/api/v1/auth/2fa/disable/", { password, code });
}

export async function regenerateRecoveryCodes(password: string, code: string): Promise<RecoveryCodesResponse> {
  return api.post<RecoveryCodesResponse>("/api/v1/auth/2fa/recovery-codes/", { password, code });
}
