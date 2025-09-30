import apiClient from "./client";

export interface UserProfile {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export async function fetchProfile() {
  const { data } = await apiClient.get<UserProfile>("/api/v1/auth/me");
  return data;
}

export interface UserToken {
  id: string;
  service: string;
  scope: string[];
  expires_at?: string | null;
  created_at: string;
}

export async function fetchAuthTokens() {
  const { data } = await apiClient.get<{ tokens: UserToken[] }>("/api/v1/auth/tokens");
  return data.tokens;
}
