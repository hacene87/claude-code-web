/**
 * API Service
 * ===========
 *
 * Axios-based API client for OAS backend.
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as Keychain from 'react-native-keychain';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  SERVER_URL: 'oas_server_url',
  ACCESS_TOKEN: 'oas_access_token',
  REFRESH_TOKEN: 'oas_refresh_token',
};

class ApiService {
  private client: AxiosInstance;
  private baseURL: string = '';

  constructor() {
    this.client = axios.create({
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        const token = await this.getAccessToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();
            const token = await this.getAccessToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            // Token refresh failed, user needs to re-login
            await this.clearTokens();
            throw refreshError;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async setServerURL(url: string): Promise<void> {
    this.baseURL = url.replace(/\/$/, '');
    this.client.defaults.baseURL = this.baseURL;
    await AsyncStorage.setItem(STORAGE_KEYS.SERVER_URL, this.baseURL);
  }

  async getServerURL(): Promise<string | null> {
    if (this.baseURL) return this.baseURL;
    const url = await AsyncStorage.getItem(STORAGE_KEYS.SERVER_URL);
    if (url) {
      this.baseURL = url;
      this.client.defaults.baseURL = url;
    }
    return url;
  }

  async setTokens(accessToken: string, refreshToken: string): Promise<void> {
    await Keychain.setGenericPassword('oas_tokens', JSON.stringify({
      access: accessToken,
      refresh: refreshToken,
    }));
  }

  async getAccessToken(): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword();
      if (credentials) {
        const tokens = JSON.parse(credentials.password);
        return tokens.access;
      }
    } catch (error) {
      console.error('Error getting access token:', error);
    }
    return null;
  }

  async getRefreshToken(): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword();
      if (credentials) {
        const tokens = JSON.parse(credentials.password);
        return tokens.refresh;
      }
    } catch (error) {
      console.error('Error getting refresh token:', error);
    }
    return null;
  }

  async clearTokens(): Promise<void> {
    await Keychain.resetGenericPassword();
  }

  private async refreshToken(): Promise<void> {
    const refreshToken = await this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post(`${this.baseURL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });

    await this.setTokens(
      response.data.access_token,
      response.data.refresh_token
    );
  }

  // Generic request methods
  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }
}

export const api = new ApiService();
export default api;
