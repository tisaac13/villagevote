/**
 * Authentication Store
 * Manages user authentication state using Zustand
 */
import { create } from 'zustand';
import { api } from '@/services/api';
import { User, UserProfile, LoginRequest, SignupRequest, Address } from '@/types';

interface AuthState {
  // State
  user: User | null;
  profile: UserProfile | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  // Actions
  initialize: () => Promise<void>;
  login: (credentials: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // Initial state
  user: null,
  profile: null,
  isLoading: false,
  isInitialized: false,
  error: null,

  // Initialize auth state from stored tokens
  initialize: async () => {
    try {
      set({ isLoading: true });

      const hasToken = await api.init();

      if (hasToken) {
        const profile = await api.getProfile();
        set({
          user: profile.user,
          profile,
          isInitialized: true,
          isLoading: false,
        });
      } else {
        set({ isInitialized: true, isLoading: false });
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      set({ isInitialized: true, isLoading: false });
    }
  },

  // Login with email and password
  login: async (credentials: LoginRequest) => {
    try {
      set({ isLoading: true, error: null });

      await api.login(credentials);
      const profile = await api.getProfile();

      set({
        user: profile.user,
        profile,
        isLoading: false,
      });
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Login failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  // Sign up new user
  signup: async (data: SignupRequest) => {
    try {
      set({ isLoading: true, error: null });

      const response = await api.signup(data);

      set({
        user: response.user,
        profile: {
          user: response.user,
          address: {
            city: data.address.city,
            state: data.address.state,
            postal_code: data.address.postal_code,
            country: data.address.country,
          },
          location: response.location,
          preferences: { topics: [], notify_enabled: true },
        },
        isLoading: false,
      });
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Signup failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  // Logout
  logout: async () => {
    try {
      await api.logout();
    } finally {
      set({ user: null, profile: null });
    }
  },

  // Refresh profile data
  refreshProfile: async () => {
    try {
      const profile = await api.getProfile();
      set({ profile, user: profile.user });
    } catch (error) {
      console.error('Failed to refresh profile:', error);
    }
  },

  // Clear error message
  clearError: () => {
    set({ error: null });
  },
}));
