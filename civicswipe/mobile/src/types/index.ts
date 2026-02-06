/**
 * CivicSwipe Type Definitions
 */

// User types
export interface User {
  id: string;
  email: string;
}

export interface Address {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface UserProfile {
  user: User;
  address: {
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  location: {
    lat: number | null;
    lon: number | null;
  };
  preferences: {
    topics: string[];
    notify_enabled: boolean;
  };
}

// Authentication types
export interface Tokens {
  access_token: string;
  refresh_token: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  address: Address;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupResponse {
  user: User;
  tokens: Tokens;
  location: {
    lat: number | null;
    lon: number | null;
    divisions_resolved: boolean;
  };
}

// Measure types
export type JurisdictionLevel = 'federal' | 'state' | 'county' | 'city';
export type MeasureStatus =
  | 'introduced'
  | 'scheduled'
  | 'in_committee'
  | 'passed'
  | 'failed'
  | 'tabled'
  | 'withdrawn'
  | 'unknown';

export interface Measure {
  id: string;
  source: string;
  external_id: string;
  title: string;
  level: JurisdictionLevel;
  status: MeasureStatus;
  introduced_at: string | null;
  scheduled_for: string | null;
  topic_tags: string[];
  summary_short: string | null;
  summary_long: string | null;
  sources: MeasureSource[];
}

export interface MeasureSource {
  id: string;
  label: string;
  url: string;
  ctype: string;
  is_primary: boolean;
}

// Vote types
export type VoteValue = 'yes' | 'no';

export interface UserVote {
  id: string;
  measure_id: string;
  vote: VoteValue;
  voted_at: string;
  measure?: Measure;
}

// Feed types
export interface FeedItem extends Measure {
  user_vote?: VoteValue;
}

// Match types
export interface MatchResult {
  official_id: string;
  official_name: string;
  match_percentage: number;
  votes_compared: number;
  agreements: number;
  disagreements: number;
}

// Navigation types
export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  Login: undefined;
  Signup: undefined;
  Onboarding: undefined;
};

export type MainTabParamList = {
  Feed: undefined;
  MyVotes: undefined;
  Match: undefined;
  Profile: undefined;
};

export type AuthStackParamList = {
  Welcome: undefined;
  Login: undefined;
  Signup: undefined;
  Address: { email: string; password: string };
};
