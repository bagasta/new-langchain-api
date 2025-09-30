import apiClient from "./client";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

function toParams(payload: LoginPayload) {
  return {
    email: payload.email,
    password: payload.password,
  };
}

export async function login(payload: LoginPayload) {
  const params = toParams(payload);
  const { data } = await apiClient.post<AuthResponse>("/api/v1/auth/login", null, {
    params,
  });
  return data;
}

export async function register(payload: LoginPayload) {
  const params = toParams(payload);
  const { data } = await apiClient.post<AuthResponse>("/api/v1/auth/register", null, {
    params,
  });
  return data;
}

export async function getGoogleAuth() {
  const { data } = await apiClient.get("/api/v1/auth/google/auth");
  return data;
}
