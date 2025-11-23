/**
 * Authentication Service
 * ======================
 */

import api from './api';
import { LoginRequest, TokenResponse, User } from '../types/api.types';

export const authService = {
  async login(serverUrl: string, credentials: LoginRequest): Promise<TokenResponse> {
    // Set server URL first
    await api.setServerURL(serverUrl);

    // Login using form data (OAuth2 format)
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post<TokenResponse>('/api/v1/auth/login', formData.toString());

    // Store tokens
    await api.setTokens(response.access_token, response.refresh_token);

    return response;
  },

  async logout(): Promise<void> {
    await api.clearTokens();
  },

  async getCurrentUser(): Promise<User> {
    return api.get<User>('/api/v1/auth/me');
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await api.getAccessToken();
    return !!token;
  },

  async refreshTokens(): Promise<TokenResponse> {
    const refreshToken = await api.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await api.post<TokenResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    await api.setTokens(response.access_token, response.refresh_token);

    return response;
  },
};

export default authService;
