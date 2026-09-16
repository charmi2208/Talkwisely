/**
 * Auth API functions
 */

import apiClient from "./client";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  organization_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string;
  organization_id: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  organization_name: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
}

export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/login", data);
    return res.data;
  },

  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/register", data);
    return res.data;
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return res.data;
  },

  me: async (): Promise<UserProfile> => {
    const res = await apiClient.get<UserProfile>("/auth/me");
    return res.data;
  },
};
