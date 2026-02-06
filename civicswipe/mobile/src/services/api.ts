/**
 * API Service
 * Handles all HTTP requests to the CivicSwipe backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';
import {
  Tokens,
  LoginRequest,
  SignupRequest,
  SignupResponse,
  UserProfile,
  Measure,
  UserVote,
  VoteValue,
  MatchResult,
} from '@/types';

// API base URL - change for production
const API_BASE_URL = __DEV__
  ? 'http://localhost:8000'
  : 'https://api.civicswipe.com';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

class ApiService {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      async (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && originalRequest) {
          try {
            await this.refreshTokens();
            originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            await this.logout();
            throw refreshError;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Initialize tokens from secure storage
  async init(): Promise<boolean> {
    try {
      this.accessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
      this.refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      return !!this.accessToken;
    } catch (error) {
      console.error('Failed to load tokens:', error);
      return false;
    }
  }

  // Save tokens to secure storage
  private async saveTokens(tokens: Tokens): Promise<void> {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.access_token);
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }

  // Clear tokens
  private async clearTokens(): Promise<void> {
    this.accessToken = null;
    this.refreshToken = null;
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  }

  // Refresh access token
  private async refreshTokens(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post<Tokens>(`${API_BASE_URL}/v1/auth/refresh`, {
      refresh_token: this.refreshToken,
    });

    await this.saveTokens(response.data);
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // ============================================================================
  // Authentication
  // ============================================================================

  async login(credentials: LoginRequest): Promise<Tokens> {
    const response = await this.client.post<Tokens>('/v1/auth/login', credentials);
    await this.saveTokens(response.data);
    return response.data;
  }

  async signup(data: SignupRequest): Promise<SignupResponse> {
    const response = await this.client.post<SignupResponse>('/v1/auth/signup', data);
    await this.saveTokens(response.data.tokens);
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/v1/auth/logout');
    } catch (error) {
      // Ignore errors during logout
    }
    await this.clearTokens();
  }

  // ============================================================================
  // Profile
  // ============================================================================

  async getProfile(): Promise<UserProfile> {
    const response = await this.client.get<UserProfile>('/v1/me');
    return response.data;
  }

  async updatePreferences(preferences: {
    topics?: string[];
    notify_enabled?: boolean;
  }): Promise<void> {
    await this.client.patch('/v1/me/preferences', preferences);
  }

  // ============================================================================
  // Measures (Feed)
  // ============================================================================

  async getFeed(params?: {
    level?: string;
    limit?: number;
    offset?: number;
  }): Promise<Measure[]> {
    const response = await this.client.get<{ measures: Measure[] }>('/v1/feed', {
      params,
    });
    return response.data.measures;
  }

  async getMeasure(measureId: string): Promise<Measure> {
    const response = await this.client.get<Measure>(`/v1/measures/${measureId}`);
    return response.data;
  }

  // ============================================================================
  // Voting
  // ============================================================================

  async vote(measureId: string, vote: VoteValue): Promise<UserVote> {
    const response = await this.client.post<UserVote>(`/v1/measures/${measureId}/vote`, {
      vote,
    });
    return response.data;
  }

  async getMyVotes(params?: {
    limit?: number;
    offset?: number;
  }): Promise<UserVote[]> {
    const response = await this.client.get<{ votes: UserVote[] }>('/v1/me/votes', {
      params,
    });
    return response.data.votes;
  }

  async deleteVote(measureId: string): Promise<void> {
    await this.client.delete(`/v1/measures/${measureId}/vote`);
  }

  // ============================================================================
  // Match
  // ============================================================================

  async getMatches(): Promise<MatchResult[]> {
    const response = await this.client.get<{ matches: MatchResult[] }>('/v1/me/matches');
    return response.data.matches;
  }
}

// Export singleton instance
export const api = new ApiService();
