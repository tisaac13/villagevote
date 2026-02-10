/**
 * VillageVote Mobile App
 * 32-bit Pokemon GameBoy Color Style
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { StatusBar } from 'expo-status-bar';
import { View, Text, ActivityIndicator, StyleSheet, TextInput, TouchableOpacity, ScrollView, Platform, Dimensions, Animated, Modal } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// API base URL — driven by Expo config or __DEV__ flag.
// Production builds always use HTTPS.
const getApiBaseUrl = (): string => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Constants = require('expo-constants').default;
    const extra = Constants?.expoConfig?.extra;
    if (extra?.apiBaseUrl) return extra.apiBaseUrl;
  } catch { /* expo-constants not available */ }

  // Development fallbacks (HTTP allowed for local dev only)
  if (__DEV__) {
    return Platform.OS === 'web'
      ? 'http://localhost:8000/v1'
      : 'http://192.168.1.195:8000/v1';
  }

  // Production — always HTTPS
  return 'https://api.villagevote.us/v1';
};

const API_BASE_URL = getApiBaseUrl();

// Secure token storage helpers — uses expo-secure-store on native, falls back to memory-only on web
const TOKEN_KEY = 'vv_session';

async function saveSession(user: Record<string, any>): Promise<void> {
  try {
    if (Platform.OS === 'web') return; // Web: no secure store, session is memory-only
    await SecureStore.setItemAsync(TOKEN_KEY, JSON.stringify(user));
  } catch { /* best-effort */ }
}

async function loadSession(): Promise<any | null> {
  try {
    if (Platform.OS === 'web') return null;
    const raw = await SecureStore.getItemAsync(TOKEN_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

async function clearSession(): Promise<void> {
  try {
    if (Platform.OS === 'web') return;
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch { /* best-effort */ }
}

// In production builds, silence console.log/warn/error to prevent leaking
// sensitive data (tokens, user info) that may appear in error messages.
if (!__DEV__) {
  console.log = () => {};
  console.warn = () => {};
  console.error = () => {};
}

// Patriotic Color Palette - Red, White, Blue & Gold
const GBC = {
  // Main blues (primary background colors)
  darkGreen: '#1a2b4c',      // Dark navy (replaces darkGreen for text)
  green: '#2c4a7c',          // Navy (replaces green)
  lightGreen: '#f5f5f5',     // Off-white/light gray (main background)
  lighterGreen: '#ffffff',   // Pure white (highlights)

  // Menu colors
  cream: '#ffffff',          // White (menu backgrounds)
  tan: '#e8e8e8',            // Light gray (borders/dividers)
  darkTan: '#c0c0c0',        // Medium gray (accents)

  // Battle/UI colors
  red: '#b22234',            // American flag red
  darkRed: '#8b0000',        // Dark red
  blue: '#3c3b6e',           // American flag blue
  darkBlue: '#1a2b4c',       // Dark navy
  yellow: '#ffd700',         // Gold
  darkYellow: '#daa520',     // Goldenrod

  // Neutral
  white: '#ffffff',
  black: '#1a1a2e',          // Dark navy-black
  gray: '#606060',
  lightGray: '#a0a0a0',

  // Special
  pixelBorder: '#1a2b4c',    // Dark navy border
  screenBg: '#0f1d33',       // Deep navy (screen background)
};

// Types
interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  access_token?: string;
  birthday?: string;
}

interface Measure {
  id: string;
  measure_id?: string;
  title: string;
  summary?: string;
  summary_short?: string;
  level?: string;
  status: string;
  sources?: { label: string; url: string }[];
  user_vote?: string;
  external_id?: string;
}

interface DashboardStats {
  total_votes: number;
  yea_votes: number;
  nay_votes: number;
  skipped: number;
  measures_passed: number;
  measures_failed: number;
  measures_pending: number;
  alignment_score: number | null;
}

interface VoteHistoryItem {
  measure_id: string;
  title: string;
  summary_short?: string;
  level: string;
  user_vote: string;
  voted_at: string;
  outcome: string | null;
  outcome_matches_user: boolean | null;
}

interface Category {
  name: string;
  topics: string[];
  count: number;
  icon: string;
}

interface Representative {
  id: string;
  name: string;
  office: string;
  party: string | null;
  chamber: string | null;
  district_label: string | null;
  photo_url: string | null;
  alignment_percentage: number | null;
  votes_compared: number;
}

// Pixel Art Box Component
function PixelBox({ children, style, variant = 'default' }: { children: React.ReactNode; style?: any; variant?: 'default' | 'menu' | 'dialog' | 'battle' }) {
  const getBoxStyle = () => {
    switch (variant) {
      case 'menu':
        return { backgroundColor: GBC.cream, borderColor: GBC.blue };
      case 'dialog':
        return { backgroundColor: GBC.white, borderColor: GBC.blue };
      case 'battle':
        return { backgroundColor: GBC.white, borderColor: GBC.blue };
      default:
        return { backgroundColor: GBC.cream, borderColor: GBC.blue };
    }
  };

  return (
    <View style={[styles.pixelBox, getBoxStyle(), style]}>
      <View style={styles.pixelBoxInner}>
        {children}
      </View>
    </View>
  );
}

// Pixel Button Component
function PixelButton({ onPress, title, variant = 'primary', disabled = false, icon }: { onPress: () => void; title: string; variant?: 'primary' | 'secondary' | 'danger' | 'success'; disabled?: boolean; icon?: string }) {
  const getButtonColors = () => {
    if (disabled) return { bg: GBC.lightGray, border: GBC.gray, text: GBC.gray };
    switch (variant) {
      case 'primary':
        return { bg: GBC.blue, border: GBC.darkBlue, text: GBC.white };
      case 'secondary':
        return { bg: GBC.tan, border: GBC.darkTan, text: GBC.black };
      case 'danger':
        return { bg: GBC.red, border: GBC.darkRed, text: GBC.white };
      case 'success':
        return { bg: GBC.yellow, border: GBC.darkYellow, text: GBC.black };
      default:
        return { bg: GBC.blue, border: GBC.darkBlue, text: GBC.white };
    }
  };

  const colors = getButtonColors();

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.pixelButton,
        { backgroundColor: colors.bg, borderColor: colors.border },
      ]}
      activeOpacity={0.7}
    >
      <Text style={[styles.pixelButtonText, { color: colors.text }]}>
        {icon ? `${icon} ` : ''}{title}
      </Text>
    </TouchableOpacity>
  );
}

// Helper functions
function simplifyTitle(title: string): string {
  let simplified = title
    .replace(/\s*\(Ordinance\s+[A-Z]?-?\d+\)\s*/gi, ' ')
    .replace(/\s*Ordinance\s+[A-Z]-?\d+\s*/gi, ' ')
    .replace(/\s*\(Resolution\s+\d+\)\s*/gi, ' ')
    .replace(/\s*-?\s*AR\d+\s*/gi, ' ')
    .replace(/\s+to\s+Include\s+Proposed\s+Revisions\s+to,?\s*/gi, ' ')
    .replace(/,?\s*Article\s+[IVXLCDM]+,?\s*(\([A-Z]\))?\s*/gi, ' ')
    .replace(/,?\s*Article\s+\d+,?\s*(\([A-Z]\))?\s*/gi, ' ')
    .replace(/\s*Section\s*\([A-Z]\)\s*/gi, ' ')
    .replace(/\s*Section\s+[\d-]+(\.\d+)?\s*/gi, ' ')
    .replace(/,?\s+and\s+\d+-\d+\s*/gi, ' ')
    .replace(/,?\s*\d+-\d+\s*/gi, ' ')
    .replace(/\s*(Phoenix\s+)?City\s+Code[^,]*/gi, ' ')
    .replace(/\s*Chapter\s+\d+[^,]*/gi, ' ')
    .replace(/\s*(Contract|Agreement)\s*(No\.?\s*)?\d+\s*/gi, ' ')
    .replace(/\s*-\s*(District\s+\d+|Citywide)\s*$/gi, '')
    .replace(/\s*\(General Obligation Bond\)\s*/gi, ' ')
    .replace(/\s*(First|Second|Third|\d+(st|nd|rd|th)?)\s*Amendment[^,]*/gi, ' ')
    .replace(/^Request\s+to\s+/i, '')
    .replace(/^An\s+Ordinance\s+(Amending|Adding|Removing)\s+/gi, '')
    .replace(/,\s*,/g, ',')
    .replace(/\s+-\s+-\s*/g, ' - ')
    .replace(/\s+-\s*$/, '')
    .replace(/:\s*$/, '')
    .replace(/\s+/g, ' ')
    .trim();

  if (simplified.length > 100) {
    const parts = simplified.split(' - ');
    if (parts.length > 1 && parts[0].length > 20) {
      simplified = parts[0];
    }
  }

  if (simplified.length > 0) {
    simplified = simplified.charAt(0).toUpperCase() + simplified.slice(1);
  }

  return simplified;
}

function cleanSummary(summary: string): string {
  return summary
    .replace(/^Here'?s?\s+(is\s+)?a\s+\d+-?\d*\s*sentence\s+summary[^:]*:\s*/i, '')
    .replace(/^Here\s+is\s+a\s+\d+-?\d*\s*sentence\s+summary[^:]*:\s*/i, '')
    .replace(/^Here'?s?\s+a\s+plain[- ]?language\s+summary[^:]*:\s*/i, '')
    .replace(/^Here'?s?\s+a\s+summary[^:]*:\s*/i, '')
    .replace(/^Summary:\s*/i, '')
    .replace(/^In plain (English|language)[,:]?\s*/i, '')
    .replace(/^This (measure|bill|ordinance|law) would\s+/i, '')
    .replace(/^Here\s+is\s+a[^:]+:\s*/i, '')
    .trim();
}

// Login Screen - Pokemon Start Menu Style
// US States for dropdown
const US_STATES = [
  { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' }, { code: 'AZ', name: 'Arizona' },
  { code: 'AR', name: 'Arkansas' }, { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' }, { code: 'FL', name: 'Florida' },
  { code: 'GA', name: 'Georgia' }, { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' }, { code: 'IA', name: 'Iowa' },
  { code: 'KS', name: 'Kansas' }, { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' }, { code: 'MA', name: 'Massachusetts' },
  { code: 'MI', name: 'Michigan' }, { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' }, { code: 'NE', name: 'Nebraska' },
  { code: 'NV', name: 'Nevada' }, { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' }, { code: 'NC', name: 'North Carolina' },
  { code: 'ND', name: 'North Dakota' }, { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' }, { code: 'RI', name: 'Rhode Island' },
  { code: 'SC', name: 'South Carolina' }, { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' }, { code: 'VT', name: 'Vermont' },
  { code: 'VA', name: 'Virginia' }, { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' }, { code: 'DC', name: 'Washington DC' }
];

function LoginScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [birthday, setBirthday] = useState('');
  const [state, setState] = useState('');

  // Auto-format birthday as MM-DD-YYYY
  const handleBirthdayChange = (text: string) => {
    // Remove all non-numeric characters
    const numbers = text.replace(/[^0-9]/g, '');

    // Format as MM-DD-YYYY
    let formatted = '';
    if (numbers.length > 0) {
      formatted = numbers.substring(0, 2);
    }
    if (numbers.length > 2) {
      formatted += '-' + numbers.substring(2, 4);
    }
    if (numbers.length > 4) {
      formatted += '-' + numbers.substring(4, 8);
    }

    setBirthday(formatted);
  };

  const [stateInput, setStateInput] = useState('');
  const [showStateSelector, setShowStateSelector] = useState(false);
  const [filteredStates, setFilteredStates] = useState(US_STATES);

  // Handle state input with auto-complete
  const handleStateInput = (text: string) => {
    setStateInput(text);
    const searchText = text.toLowerCase().trim();

    if (searchText === '') {
      setFilteredStates(US_STATES);
      setState('');
      return;
    }

    // Filter states by code or name
    const filtered = US_STATES.filter(s =>
      s.code.toLowerCase().startsWith(searchText) ||
      s.name.toLowerCase().startsWith(searchText) ||
      s.name.toLowerCase().includes(searchText)
    );

    setFilteredStates(filtered);

    // Auto-select if exact match on code (2 chars)
    if (text.length === 2) {
      const exactMatch = US_STATES.find(s => s.code.toLowerCase() === searchText);
      if (exactMatch) {
        setState(exactMatch.code);
        setStateInput(exactMatch.name);
        setShowStateSelector(false);
        return;
      }
    }

    // Auto-select if only one match
    if (filtered.length === 1) {
      setState(filtered[0].code);
      setStateInput(filtered[0].name);
      setShowStateSelector(false);
    } else if (filtered.length > 0) {
      setShowStateSelector(true);
    }
  };

  const selectState = (stateCode: string) => {
    const selectedState = US_STATES.find(s => s.code === stateCode);
    if (selectedState) {
      setState(selectedState.code);
      setStateInput(selectedState.name);
    }
    setShowStateSelector(false);
  };
  // Optional address fields
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [addressLine1, setAddressLine1] = useState('');
  const [addressCity, setAddressCity] = useState('');
  const [addressPostalCode, setAddressPostalCode] = useState('');

  const handleLogin = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (Array.isArray(data.detail)) {
          throw new Error(data.detail.map((e: any) => e.msg).join(', '));
        }
        throw new Error(data.detail || 'Login failed');
      }

      const profileResponse = await fetch(`${API_BASE_URL}/me`, {
        headers: { 'Authorization': `Bearer ${data.access_token}` },
      });

      if (profileResponse.ok) {
        const profileData = await profileResponse.json();
        onLogin({
          id: profileData.id,
          email: profileData.email,
          first_name: profileData.first_name || email.split('@')[0],
          last_name: profileData.last_name || '',
          access_token: data.access_token,
        });
      } else {
        onLogin({
          id: 'logged-in',
          email: email,
          first_name: email.split('@')[0],
          last_name: '',
          access_token: data.access_token,
        });
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async () => {
    // Validation
    if (!firstName.trim()) {
      setError('First name is required');
      return;
    }
    if (!lastName.trim()) {
      setError('Last name is required');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (!birthday) {
      setError('Birthday is required');
      return;
    }
    if (!state) {
      setError('State is required');
      return;
    }
    // Validate birthday format (MM-DD-YYYY) and convert to YYYY-MM-DD for API
    const birthdayParts = birthday.split('-');
    if (birthdayParts.length !== 3) {
      setError('Invalid birthday format (use MM-DD-YYYY)');
      return;
    }
    const [month, day, year] = birthdayParts;
    if (!day || !month || !year || day.length !== 2 || month.length !== 2 || year.length !== 4) {
      setError('Invalid birthday format (use MM-DD-YYYY)');
      return;
    }
    const birthdayDate = new Date(`${year}-${month}-${day}`);
    if (isNaN(birthdayDate.getTime())) {
      setError('Invalid birthday');
      return;
    }
    // Check age (must be at least 13, max 120)
    const today = new Date();
    const age = today.getFullYear() - birthdayDate.getFullYear();
    if (age < 13) {
      setError('Must be at least 13 years old');
      return;
    }
    if (age > 120) {
      setError('Invalid birthday');
      return;
    }
    // Convert to YYYY-MM-DD for API
    const birthdayForAPI = `${year}-${month}-${day}`;

    setIsLoading(true);
    setError('');
    try {
      const signupData: any = {
        email,
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        birthday: birthdayForAPI,
        state: state,
      };

      // Add address if provided
      if (showAddressForm && addressLine1 && addressCity && addressPostalCode) {
        signupData.address = {
          line1: addressLine1,
          city: addressCity,
          state: state,
          postal_code: addressPostalCode,
          country: 'US'
        };
      }

      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupData),
      });

      const data = await response.json();

      if (!response.ok) {
        if (Array.isArray(data.detail)) {
          throw new Error(data.detail.map((e: any) => e.msg).join(', '));
        }
        throw new Error(data.detail || 'Signup failed');
      }

      onLogin({
        ...data.user,
        first_name: firstName,
        last_name: lastName,
        access_token: data.tokens.access_token,
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView
      style={styles.loginScrollView}
      contentContainerStyle={styles.loginScrollContent}
      keyboardShouldPersistTaps="handled"
    >
      {/* Title Banner */}
      <View style={styles.titleBanner}>
        <Text style={styles.titlePixelArt}>🏘️</Text>
        <Text style={styles.gameTitle}>VILLAGEVOTE</Text>
        <Text style={styles.titleSubtext}>By the People. For your People.</Text>
      </View>

      <PixelBox variant="menu" style={styles.loginBox}>
        <Text style={styles.menuTitle}>{isSignup ? 'SIGN UP' : 'LOG IN'}</Text>

        {isSignup && (
          <>
            <View style={styles.inputRow}>
              <Text style={styles.inputLabel}>FIRST NAME:</Text>
              <TextInput
                style={styles.pixelInput}
                placeholder="First"
                value={firstName}
                onChangeText={setFirstName}
                placeholderTextColor={GBC.lightGray}
              />
            </View>
            <View style={styles.inputRow}>
              <Text style={styles.inputLabel}>LAST NAME:</Text>
              <TextInput
                style={styles.pixelInput}
                placeholder="Last"
                value={lastName}
                onChangeText={setLastName}
                placeholderTextColor={GBC.lightGray}
              />
            </View>
            <View style={styles.inputRow}>
              <Text style={styles.inputLabel}>BIRTHDAY:</Text>
              <TextInput
                style={styles.pixelInput}
                placeholder="MMDDYYYY"
                value={birthday}
                onChangeText={handleBirthdayChange}
                placeholderTextColor={GBC.lightGray}
                keyboardType="number-pad"
                maxLength={10}
              />
            </View>
            <View style={styles.inputRow}>
              <Text style={styles.inputLabel}>STATE:</Text>
              <TextInput
                style={styles.pixelInput}
                placeholder="Type state name or code"
                value={stateInput}
                onChangeText={handleStateInput}
                onFocus={() => setShowStateSelector(true)}
                placeholderTextColor={GBC.lightGray}
                autoCapitalize="words"
              />
            </View>
            {showStateSelector && filteredStates.length > 0 && stateInput.length > 0 && !state && (
              <View style={styles.stateDropdown}>
                {filteredStates.slice(0, 5).map((s) => (
                  <TouchableOpacity
                    key={s.code}
                    style={styles.stateDropdownItem}
                    onPress={() => selectState(s.code)}
                  >
                    <Text style={styles.stateDropdownText}>{s.code} - {s.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {/* Optional Address Section */}
            <TouchableOpacity
              style={styles.addressToggle}
              onPress={() => setShowAddressForm(!showAddressForm)}
            >
              <Text style={styles.addressToggleText}>
                {showAddressForm ? '▼ HIDE ADDRESS' : '▶ ADD ADDRESS (OPTIONAL)'}
              </Text>
            </TouchableOpacity>

            {!showAddressForm && (
              <Text style={styles.addressHint}>
                Optional: Enter your address to receive local updates in the future.
              </Text>
            )}

            {showAddressForm && (
              <>
                <Text style={styles.addressHint}>
                  Optional: Enter your address to receive local updates in the future.
                </Text>
                <View style={styles.inputRow}>
                  <Text style={styles.inputLabel}>ADDRESS:</Text>
                  <TextInput
                    style={styles.pixelInput}
                    placeholder="123 Main St"
                    value={addressLine1}
                    onChangeText={setAddressLine1}
                    placeholderTextColor={GBC.lightGray}
                  />
                </View>
                <View style={styles.inputRow}>
                  <Text style={styles.inputLabel}>CITY:</Text>
                  <TextInput
                    style={styles.pixelInput}
                    placeholder="Phoenix"
                    value={addressCity}
                    onChangeText={setAddressCity}
                    placeholderTextColor={GBC.lightGray}
                  />
                </View>
                <View style={styles.inputRow}>
                  <Text style={styles.inputLabel}>ZIP:</Text>
                  <TextInput
                    style={styles.pixelInput}
                    placeholder="85001"
                    value={addressPostalCode}
                    onChangeText={setAddressPostalCode}
                    placeholderTextColor={GBC.lightGray}
                    keyboardType="number-pad"
                  />
                </View>
              </>
            )}
          </>
        )}

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>EMAIL:</Text>
          <TextInput
            style={styles.pixelInput}
            placeholder="you@email.com"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            placeholderTextColor={GBC.lightGray}
          />
        </View>

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>PASSWORD:</Text>
          <TextInput
            style={styles.pixelInput}
            placeholder="••••••••"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholderTextColor={GBC.lightGray}
          />
        </View>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorPixelText}>⚠ {error}</Text>
          </View>
        ) : null}

        <View style={styles.buttonRow}>
          <PixelButton
            onPress={isSignup ? handleSignup : handleLogin}
            title={isLoading ? 'LOADING...' : (isSignup ? 'START!' : 'GO!')}
            variant="primary"
            disabled={isLoading}
            icon="▶"
          />
        </View>

        <TouchableOpacity onPress={() => setIsSignup(!isSignup)} style={styles.switchButton}>
          <Text style={styles.switchText}>
            {isSignup ? '◄ Back to Login' : '► New Voter? Sign Up!'}
          </Text>
        </TouchableOpacity>
      </PixelBox>

      <Text style={styles.versionTextStatic}>Ver 1.0.0 © 2026 VillageVote</Text>
    </ScrollView>
  );
}

// Stat Display Component (Pokemon style)
function StatDisplay({ label, value, color, icon }: { label: string; value: number | string; color?: string; icon?: string }) {
  return (
    <View style={styles.statDisplay}>
      <Text style={styles.statIcon}>{icon}</Text>
      <View style={styles.statInfo}>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={[styles.statValue, color ? { color } : null]}>{value}</Text>
      </View>
    </View>
  );
}

// Home Dashboard Screen - Pokemon Menu Style
function HomeScreen({ user, onNavigate, onSelectCategory, scrollToCategories = false, feedMode, onSetFeedMode }: { user: User; onNavigate: (screen: string, options?: { scrollToCategories?: boolean }) => void; onSelectCategory: (category: Category | null) => void; scrollToCategories?: boolean; feedMode: 'upcoming' | 'historical'; onSetFeedMode: (mode: 'upcoming' | 'historical') => void }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [representatives, setRepresentatives] = useState<Representative[]>([]);
  const [hasAddress, setHasAddress] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  // Address form state
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [addrStreet, setAddrStreet] = useState('');
  const [addrCity, setAddrCity] = useState('');
  const [addrState, setAddrState] = useState('');
  const [addrZip, setAddrZip] = useState('');
  const [addrSuggestions, setAddrSuggestions] = useState<{ matchedAddress: string; coordinates: { x: number; y: number }; addressComponents: any }[]>([]);
  const [addrSaving, setAddrSaving] = useState(false);
  const [addrError, setAddrError] = useState('');
  const addrDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Saved address from profile (city/state/zip only - street is encrypted server-side)
  const [savedAddr, setSavedAddr] = useState<{ city: string; state: string; zip: string } | null>(null);

  useEffect(() => {
    loadDashboard();
    loadRepresentatives();
    loadSavedAddress();
  }, []);

  useEffect(() => {
    loadCategories();
  }, [feedMode]);

  const loadDashboard = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/dashboard`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/categories?mode=${feedMode}`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadRepresentatives = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/representatives`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setRepresentatives(data.representatives || []);
        setHasAddress(data.has_address !== false);
      }
    } catch (err) {
      console.error('Failed to load representatives:', err);
    }
  };

  const loadSavedAddress = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/me`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.address && data.address.city) {
          setSavedAddr({
            city: data.address.city,
            state: data.address.state || '',
            zip: data.address.postal_code || '',
          });
        }
      }
    } catch (err) {
      // Non-critical - just won't pre-fill
    }
  };

  const openAddressModal = () => {
    setAddrError('');
    setAddrSuggestions([]);
    // Pre-fill with saved address if editing (street is encrypted, so leave blank)
    if (savedAddr) {
      setAddrStreet('');
      setAddrCity(savedAddr.city);
      setAddrState(savedAddr.state);
      setAddrZip(savedAddr.zip);
    } else {
      setAddrStreet('');
      setAddrCity('');
      setAddrState('');
      setAddrZip('');
    }
    setShowAddressModal(true);
  };

  const getAlignmentColor = (pct: number | null) => {
    if (pct === null) return GBC.gray;
    if (pct >= 60) return '#2e8b57';
    if (pct >= 40) return GBC.darkYellow;
    return GBC.red;
  };

  const getPartyLabel = (party: string | null) => {
    if (!party) return '';
    if (party.startsWith('R')) return '(R)';
    if (party.startsWith('D')) return '(D)';
    if (party.startsWith('I') || party.startsWith('Ind')) return '(I)';
    return `(${party.charAt(0)})`;
  };

  const handleCategorySelect = (category: Category) => {
    onSelectCategory(category);
    onNavigate('feed');
  };

  // Census Geocoder autocomplete - fires as user types street address
  const searchAddress = (street: string) => {
    setAddrStreet(street);
    if (addrDebounceRef.current) clearTimeout(addrDebounceRef.current);
    if (street.length < 5) {
      setAddrSuggestions([]);
      return;
    }
    addrDebounceRef.current = setTimeout(async () => {
      try {
        const onelineAddr = `${street}, ${addrCity || ''}, ${addrState || ''} ${addrZip || ''}`.trim();
        const url = `https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encodeURIComponent(onelineAddr)}&benchmark=Public_AR_Current&format=json`;
        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          const matches = data?.result?.addressMatches || [];
          setAddrSuggestions(matches.slice(0, 5));
        }
      } catch (err) {
        console.error('Address search failed:', err);
      }
    }, 400);
  };

  const selectSuggestion = (suggestion: any) => {
    const components = suggestion.addressComponents || {};
    setAddrStreet(suggestion.matchedAddress?.split(',')[0] || addrStreet);
    setAddrCity(components.city || addrCity);
    setAddrState(components.state || addrState);
    setAddrZip(components.zip || addrZip);
    setAddrSuggestions([]);
  };

  const saveAddress = async () => {
    if (!addrStreet || !addrCity || !addrState || !addrZip) return;
    setAddrSaving(true);
    setAddrError('');
    try {
      const response = await fetch(`${API_BASE_URL}/me/address`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          line1: addrStreet,
          city: addrCity,
          state: addrState,
          postal_code: addrZip,
          country: 'US',
        }),
      });
      if (response.ok) {
        // Update saved address for future edits
        setSavedAddr({ city: addrCity, state: addrState, zip: addrZip });
        setShowAddressModal(false);
        setHasAddress(true);
        // Refresh representatives after address update
        loadRepresentatives();
      } else {
        const data = await response.json().catch(() => null);
        setAddrError(data?.detail || 'Failed to save address. Please try again.');
      }
    } catch (err) {
      setAddrError('Network error. Please check your connection.');
    } finally {
      setAddrSaving(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.gbcLoadingContainer}>
        <Text style={styles.loadingPixel}>Loading...</Text>
        <View style={styles.pixelLoader}>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={styles.gbcScrollView}>
      {/* Trainer Card - hide when scrollToCategories */}
      {!scrollToCategories && (
        <PixelBox variant="menu" style={styles.trainerCard}>
          <View style={styles.trainerHeader}>
            <Text style={styles.trainerSprite}>👤</Text>
            <View style={styles.trainerInfo}>
              <Text style={styles.trainerName}>{user.first_name.toUpperCase()}</Text>
              <Text style={styles.trainerTitle}>VOTER</Text>
            </View>
          </View>
        </PixelBox>
      )}

      {/* Stats Box - hide when scrollToCategories */}
      {!scrollToCategories && stats && (
        <PixelBox variant="dialog" style={styles.statsBox}>
          <Text style={styles.boxTitle}>═══ YOUR VOTES ═══</Text>

          <View style={styles.statsGrid}>
            <StatDisplay label="TOTAL" value={stats.total_votes} icon="📊" />
            <StatDisplay label="YEA" value={stats.yea_votes} color="#2e8b57" icon="✓" />
            <StatDisplay label="NAY" value={stats.nay_votes} color={GBC.red} icon="✗" />
            <StatDisplay label="SKIP" value={stats.skipped} color={GBC.gray} icon="→" />
          </View>

          <View style={styles.dividerPixel} />

          <View style={styles.statsGrid}>
            <StatDisplay label="PASSED" value={stats.measures_passed} color="#2e8b57" icon="🏆" />
            <StatDisplay label="FAILED" value={stats.measures_failed} color={GBC.red} icon="💔" />
            <StatDisplay label="PENDING" value={stats.measures_pending} icon="⏳" />
            {stats.alignment_score !== null && (
              <StatDisplay label="ALIGN" value={`${stats.alignment_score}%`} color={GBC.blue} icon="🎯" />
            )}
          </View>
        </PixelBox>
      )}

      {/* Representatives Section - hide when scrollToCategories */}
      {!scrollToCategories && (
        <PixelBox variant="dialog" style={styles.repsBox}>
          <Text style={styles.boxTitle}>═══ YOUR REPRESENTATIVES ═══</Text>

          {!hasAddress || representatives.length === 0 ? (
            <View style={styles.repsEmpty}>
              <Text style={styles.repsEmptyIcon}>🏛️</Text>
              <Text style={styles.repsEmptyText}>
                {!hasAddress ? 'ENTER YOUR ADDRESS' : 'NO REPS FOUND'}
              </Text>
              <Text style={styles.repsEmptySubtext}>
                {!hasAddress ? 'to see your representatives' : 'Update your address to find representatives'}
              </Text>
              <TouchableOpacity
                style={styles.addAddressButton}
                onPress={openAddressModal}
              >
                <Text style={styles.addAddressButtonText}>
                  {!hasAddress ? 'ADD ADDRESS' : 'UPDATE ADDRESS'}
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              {representatives.map((rep) => (
                <View key={rep.id} style={styles.repCard}>
                  <View style={styles.repHeader}>
                    <Text style={styles.repSprite}>🏛️</Text>
                    <View style={styles.repInfo}>
                      <Text style={styles.repName}>
                        {rep.name.toUpperCase()} {getPartyLabel(rep.party)}
                      </Text>
                      <Text style={styles.repOffice}>
                        {rep.office}{rep.district_label ? ` - ${rep.district_label}` : ''}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.repAlignment}>
                    {rep.alignment_percentage !== null ? (
                      <>
                        <Text style={[styles.repAlignValue, { color: getAlignmentColor(rep.alignment_percentage) }]}>
                          {rep.alignment_percentage}%
                        </Text>
                        <Text style={styles.repAlignLabel}>ALIGN ({rep.votes_compared})</Text>
                      </>
                    ) : (
                      <Text style={styles.repAlignLabel}>NO VOTES YET</Text>
                    )}
                  </View>
                </View>
              ))}
              <TouchableOpacity
                style={styles.updateAddressLink}
                onPress={openAddressModal}
              >
                <Text style={styles.updateAddressLinkText}>UPDATE ADDRESS</Text>
              </TouchableOpacity>
            </>
          )}
        </PixelBox>
      )}

      {/* Address Entry Modal */}
      <Modal visible={showAddressModal} animationType="slide" transparent>
        <View style={styles.addrModalOverlay}>
          <View style={styles.addrModalContainer}>
            <PixelBox variant="dialog" style={styles.addrModalBox}>
              <Text style={styles.boxTitle}>{savedAddr ? '═══ UPDATE ADDRESS ═══' : '═══ ENTER ADDRESS ═══'}</Text>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>STREET:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="123 Main St"
                  value={addrStreet}
                  onChangeText={searchAddress}
                  placeholderTextColor={GBC.lightGray}
                  autoFocus
                />
              </View>

              {addrSuggestions.length > 0 && (
                <View style={styles.addrSuggestions}>
                  {addrSuggestions.map((s, i) => (
                    <TouchableOpacity
                      key={i}
                      style={styles.addrSuggestionItem}
                      onPress={() => selectSuggestion(s)}
                    >
                      <Text style={styles.addrSuggestionText} numberOfLines={1}>
                        {s.matchedAddress}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>CITY:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="Phoenix"
                  value={addrCity}
                  onChangeText={setAddrCity}
                  placeholderTextColor={GBC.lightGray}
                />
              </View>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>STATE:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="AZ"
                  value={addrState}
                  onChangeText={(t) => setAddrState(t.toUpperCase().slice(0, 2))}
                  placeholderTextColor={GBC.lightGray}
                  autoCapitalize="characters"
                  maxLength={2}
                />
              </View>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>ZIP:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="85001"
                  value={addrZip}
                  onChangeText={setAddrZip}
                  placeholderTextColor={GBC.lightGray}
                  keyboardType="number-pad"
                />
              </View>

              {addrError ? (
                <Text style={styles.addrErrorText}>{addrError}</Text>
              ) : null}

              <View style={styles.addrButtonRow}>
                <TouchableOpacity
                  style={styles.addrCancelButton}
                  onPress={() => { setShowAddressModal(false); setAddrSuggestions([]); setAddrError(''); }}
                >
                  <Text style={styles.addrCancelText}>CANCEL</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.addrSaveButton, (!addrStreet || !addrCity || !addrState || !addrZip) && { opacity: 0.5 }]}
                  onPress={saveAddress}
                  disabled={!addrStreet || !addrCity || !addrState || !addrZip || addrSaving}
                >
                  <Text style={styles.addrSaveText}>{addrSaving ? 'SAVING...' : 'SAVE'}</Text>
                </TouchableOpacity>
              </View>
            </PixelBox>
          </View>
        </View>
      </Modal>

      {/* Vote by Category */}
      <View>
        <PixelBox variant="menu" style={styles.categoryBox}>
          <Text style={styles.boxTitle}>═══ VOTE BY CATEGORY ═══</Text>

          {/* Mode toggle: Upcoming vs Historical */}
          <View style={styles.feedModeToggle}>
            <TouchableOpacity
              style={[styles.feedModeBtn, feedMode === 'upcoming' && styles.feedModeBtnActive]}
              onPress={() => onSetFeedMode('upcoming')}
            >
              <Text style={[styles.feedModeBtnText, feedMode === 'upcoming' && styles.feedModeBtnTextActive]}>📋 UPCOMING</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.feedModeBtn, feedMode === 'historical' && styles.feedModeBtnActive]}
              onPress={() => onSetFeedMode('historical')}
            >
              <Text style={[styles.feedModeBtnText, feedMode === 'historical' && styles.feedModeBtnTextActive]}>📜 HISTORICAL</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.allBillsButton}
            onPress={() => { onSelectCategory(null); onNavigate('feed'); }}
          >
          <Text style={styles.allBillsIcon}>🗳️</Text>
          <Text style={styles.allBillsText}>{feedMode === 'historical' ? 'ALL HISTORICAL' : 'ALL UPCOMING'}</Text>
          <Text style={styles.allBillsArrow}>►</Text>
        </TouchableOpacity>

        <View style={styles.categoryGrid}>
          {categories.map((category) => (
            <TouchableOpacity
              key={category.name}
              style={styles.categoryButton}
              onPress={() => handleCategorySelect(category)}
            >
              <Text style={styles.categoryIcon}>{category.icon}</Text>
              <Text style={styles.categoryName}>{category.name.toUpperCase()}</Text>
              <Text style={styles.categoryCount}>{category.count}</Text>
            </TouchableOpacity>
          ))}
        </View>
        </PixelBox>
      </View>

    </ScrollView>
  );
}

// Vote History Screen - Pokemon Pokedex Style
function HistoryScreen({ user, onNavigate }: { user: User; onNavigate: (screen: string, options?: { scrollToCategories?: boolean }) => void }) {
  const [votes, setVotes] = useState<VoteHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadHistory();
  }, [filter]);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      let url = `${API_BASE_URL}/my-votes?limit=50`;
      if (filter !== 'all') {
        url += `&outcome=${filter}`;
      }
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setVotes(data.items || []);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getVoteSprite = (vote: string) => {
    if (vote === 'yes') return '✓';
    if (vote === 'no') return '✗';
    return '→';
  };

  const getOutcomeSprite = (outcome: string | null, matches: boolean | null) => {
    if (!outcome) return '⏳';
    if (matches) return '🏆';
    return '💔';
  };

  const getLevelBadge = (level: string, externalId?: string) => {
    // For federal bills, show HOUSE or SENATE based on external_id
    if (level === 'federal' && externalId) {
      if (externalId.includes('-hr-')) {
        return { text: 'HOUSE', color: GBC.darkBlue };
      } else if (externalId.includes('-s-')) {
        return { text: 'SENATE', color: GBC.blue };
      }
      return { text: 'FED', color: GBC.darkBlue };
    }
    switch (level) {
      case 'federal': return { text: 'FED', color: GBC.blue };
      case 'state': return { text: 'STATE', color: GBC.red };
      case 'city': return { text: 'LOCAL', color: '#2c7a2c' };  // Green for local
      default: return { text: '???', color: GBC.gray };
    }
  };

  return (
    <View style={styles.historyGbcContainer}>
      {/* Filter Tabs - Pokemon style */}
      <View style={styles.filterTabsGbc}>
        {['all', 'passed', 'failed', 'pending'].map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterTabGbc, filter === f && styles.filterTabGbcActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterTabTextGbc, filter === f && styles.filterTabTextGbcActive]}>
              {f.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {isLoading ? (
        <View style={styles.gbcLoadingContainer}>
          <Text style={styles.loadingPixel}>Searching...</Text>
        </View>
      ) : votes.length === 0 ? (
        <PixelBox variant="dialog" style={styles.emptyHistoryBox}>
          <Text style={styles.emptyHistoryText}>No votes recorded!</Text>
          <Text style={styles.emptyHistorySubtext}>Start voting to fill your VOTEDEX!</Text>
          <PixelButton onPress={() => onNavigate('feed')} title="GO VOTE!" variant="primary" icon="▶" />
        </PixelBox>
      ) : (
        <ScrollView style={styles.historyListGbc}>
          {votes.map((item, index) => {
            const levelBadge = getLevelBadge(item.level);
            return (
              <PixelBox key={item.measure_id} variant="menu" style={styles.historyItemGbc}>
                <View style={styles.historyItemHeader}>
                  <Text style={styles.historyItemNumber}>#{String(index + 1).padStart(3, '0')}</Text>
                  <View style={[styles.levelBadgeGbc, { backgroundColor: levelBadge.color }]}>
                    <Text style={styles.levelBadgeTextGbc}>{levelBadge.text}</Text>
                  </View>
                  <Text style={styles.historyOutcomeSprite}>
                    {getOutcomeSprite(item.outcome, item.outcome_matches_user)}
                  </Text>
                </View>

                <Text style={styles.historyItemTitle} numberOfLines={2}>
                  {simplifyTitle(item.title)}
                </Text>

                {item.summary_short && (
                  <Text style={styles.historyItemSummary} numberOfLines={3}>
                    {cleanSummary(item.summary_short)}
                  </Text>
                )}

                <View style={styles.historyItemFooter}>
                  <View style={styles.voteIndicator}>
                    <Text style={styles.voteLabel}>YOUR VOTE:</Text>
                    <Text style={[
                      styles.voteValue,
                      { color: item.user_vote === 'yes' ? '#2e8b57' : item.user_vote === 'no' ? GBC.red : GBC.gray }
                    ]}>
                      {getVoteSprite(item.user_vote)} {item.user_vote === 'yes' ? 'YEA' : item.user_vote === 'no' ? 'NAY' : 'SKIP'}
                    </Text>
                  </View>
                  <Text style={styles.outcomeText}>
                    {item.outcome ? item.outcome.toUpperCase() : 'PENDING'}
                  </Text>
                </View>
              </PixelBox>
            );
          })}
        </ScrollView>
      )}
    </View>
  );
}

// Swipe Card Component - Pokemon Battle Card Style
function SwipeCard({ measure, onVote }: { measure: Measure; onVote: (vote: 'yea' | 'nay' | 'skip') => void }) {
  const scrollViewRef = useRef<ScrollView>(null);
  const level = measure.level || 'unknown';
  const rawSummary = measure.summary || measure.summary_short || 'No summary available.';
  const summary = cleanSummary(rawSummary);
  const displayTitle = simplifyTitle(measure.title);
  const wasSkipped = measure.user_vote === 'skip';

  // Scroll to top when measure changes
  useEffect(() => {
    if (scrollViewRef.current) {
      scrollViewRef.current.scrollTo({ y: 0, animated: false });
    }
  }, [measure.id]);

  const getLevelInfo = (level: string, externalId?: string) => {
    // For federal bills, show HOUSE or SENATE based on external_id
    if (level === 'federal' && externalId) {
      if (externalId.includes('-hr-')) {
        return { name: 'HOUSE', color: GBC.red, type: '🏛️' };
      } else if (externalId.includes('-s-')) {
        return { name: 'SENATE', color: GBC.blue, type: '🏛️' };
      }
    }
    switch (level) {
      case 'federal': return { name: 'CONGRESS', color: GBC.blue, type: '🏛️' };
      case 'state': return { name: 'STATE', color: GBC.red, type: '🏢' };
      case 'city': return { name: 'LOCAL', color: '#2c7a2c', type: '🏘️' };  // Keep green for local
      default: return { name: '???', color: GBC.gray, type: '❓' };
    }
  };

  const levelInfo = getLevelInfo(level, measure.external_id);

  return (
    <View style={styles.battleContainer}>
      {/* Bill "Pokemon" Card */}
      <PixelBox variant="battle" style={styles.billCard}>
        {/* Header - like Pokemon name plate */}
        <View style={styles.billHeader}>
          <View style={[styles.typeBadge, { backgroundColor: levelInfo.color }]}>
            <Text style={styles.typeBadgeText}>{levelInfo.type} {levelInfo.name}</Text>
          </View>
          {(measure.status === 'passed' || measure.status === 'failed') && (
            <View style={[styles.outcomeBadge, { backgroundColor: measure.status === 'passed' ? '#2e8b57' : GBC.red }]}>
              <Text style={styles.outcomeBadgeText}>{measure.status === 'passed' ? '✓ PASSED' : '✗ FAILED'}</Text>
            </View>
          )}
          {wasSkipped && (
            <View style={styles.skippedBadgeGbc}>
              <Text style={styles.skippedBadgeText}>◄ SKIPPED</Text>
            </View>
          )}
        </View>

        {/* Bill Name */}
        <Text style={styles.billName} numberOfLines={3}>{displayTitle}</Text>

        {/* HP-style Status Bar */}
        <View style={styles.statusBarContainer}>
          <Text style={styles.statusLabel}>STATUS:</Text>
          <View style={styles.statusBar}>
            <Text style={styles.statusValue}>{measure.status.toUpperCase()}</Text>
          </View>
        </View>

        {/* Summary - like Pokemon description */}
        <View style={styles.descriptionBox}>
          <ScrollView ref={scrollViewRef} style={styles.descriptionScroll}>
            <Text style={styles.descriptionText}>{summary}</Text>
          </ScrollView>
        </View>
      </PixelBox>

      {/* Battle Menu - Vote Buttons */}
      <PixelBox variant="menu" style={styles.battleMenu}>
        <Text style={styles.battlePrompt}>What will you do?</Text>

        <View style={styles.battleOptions}>
          <TouchableOpacity
            style={[styles.battleOption, styles.yeaOption]}
            onPress={() => onVote('yea')}
          >
            <Text style={styles.battleOptionText}>✓ YEA</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.battleOption, styles.nayOption]}
            onPress={() => onVote('nay')}
          >
            <Text style={styles.battleOptionText}>✗ NAY</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.battleOption, styles.skipOption]}
            onPress={() => onVote('skip')}
          >
            <Text style={[styles.battleOptionText, { color: GBC.gray }]}>→ SKIP</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.battleOption, styles.infoOption]}>
            <Text style={[styles.battleOptionText, { color: GBC.blue }]}>? INFO</Text>
          </TouchableOpacity>
        </View>
      </PixelBox>
    </View>
  );
}

// Feed Screen - Pokemon Battle Style
function FeedScreen({ user, onNavigate, selectedCategory, onClearCategory, feedMode, onSetFeedMode }: { user: User; onNavigate: (screen: string, options?: { scrollToCategories?: boolean }) => void; selectedCategory: Category | null; onClearCategory: () => void; feedMode: 'upcoming' | 'historical'; onSetFeedMode: (mode: 'upcoming' | 'historical') => void }) {
  const [measures, setMeasures] = useState<Measure[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [votesCount, setVotesCount] = useState(0);
  const [totalRemaining, setTotalRemaining] = useState(0);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const fetchingRef = useRef(false); // guard against concurrent fetches

  const BATCH_SIZE = 30;
  const PREFETCH_THRESHOLD = 5; // load next batch when 5 bills left in current batch

  useEffect(() => {
    loadMeasures();
  }, [selectedCategory, feedMode]);

  // Auto-fetch next batch when user nears end of current batch
  useEffect(() => {
    const billsLeft = measures.length - currentIndex;
    // Prefetch when approaching end, or emergency fetch when past the end
    if (nextCursor && !fetchingRef.current) {
      if ((billsLeft <= PREFETCH_THRESHOLD && billsLeft > 0) || (billsLeft <= 0 && totalRemaining > 0)) {
        fetchMoreMeasures();
      }
    }
  }, [currentIndex, measures.length, nextCursor, totalRemaining]);

  const buildFeedUrl = (cursor?: string | null) => {
    let url = `${API_BASE_URL}/feed?limit=${BATCH_SIZE}&include_skipped=true&mode=${feedMode}`;
    if (selectedCategory && selectedCategory.topics.length > 0) {
      url += `&topic=${encodeURIComponent(selectedCategory.topics[0])}`;
    }
    if (cursor) {
      url += `&cursor=${encodeURIComponent(cursor)}`;
    }
    return url;
  };

  const parseFeedItems = (data: any): Measure[] => {
    return (data.items || []).map((item: any) => ({
      id: item.measure_id || item.id,
      title: item.title,
      summary: item.summary_short || item.summary || '',
      level: item.level,
      status: item.status,
      sources: item.sources,
      user_vote: item.user_vote,
      external_id: item.external_id,
    }));
  };

  const loadMeasures = async () => {
    setIsLoading(true);
    setCurrentIndex(0);
    setVotesCount(0);
    setNextCursor(null);
    try {
      const response = await fetch(buildFeedUrl(), {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      const data = await response.json();
      const items = parseFeedItems(data);
      setMeasures(items);
      setTotalRemaining(data.total_remaining ?? items.length);
      setNextCursor(data.next_cursor ?? null);
    } catch (err) {
      console.error('Failed to load measures:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMoreMeasures = async () => {
    if (fetchingRef.current || !nextCursor) return;
    fetchingRef.current = true;
    setIsFetchingMore(true);
    try {
      const response = await fetch(buildFeedUrl(nextCursor), {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      const data = await response.json();
      const newItems = parseFeedItems(data);
      if (newItems.length > 0) {
        setMeasures(prev => [...prev, ...newItems]);
      }
      setTotalRemaining(data.total_remaining ?? totalRemaining);
      setNextCursor(data.next_cursor ?? null);
    } catch (err) {
      console.error('Failed to load more measures:', err);
    } finally {
      setIsFetchingMore(false);
      fetchingRef.current = false;
    }
  };

  const handleVote = async (vote: 'yea' | 'nay' | 'skip') => {
    const currentMeasure = measures[currentIndex];
    if (!currentMeasure) return;

    try {
      await fetch(`${API_BASE_URL}/measures/${currentMeasure.id}/swipe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vote: vote === 'yea' ? 'yes' : vote === 'nay' ? 'no' : 'skip' }),
      });
    } catch (err) {
      console.error('Failed to record vote:', err);
    }

    if (vote !== 'skip') {
      setVotesCount(prev => prev + 1);
    }
    // Decrement total remaining as user processes each bill
    setTotalRemaining(prev => Math.max(0, prev - 1));
    setCurrentIndex(prev => prev + 1);
  };

  if (isLoading) {
    return (
      <View style={styles.gbcLoadingContainer}>
        <Text style={styles.loadingPixel}>Loading bills...</Text>
        <View style={styles.pixelLoader}>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
        </View>
      </View>
    );
  }

  const currentMeasure = measures[currentIndex];

  return (
    <View style={styles.feedGbcContainer}>
      {/* Feed Mode Toggle */}
      <View style={styles.filterTabsGbc}>
        {(['upcoming', 'historical'] as const).map((m) => (
          <TouchableOpacity
            key={m}
            style={[styles.filterTabGbc, feedMode === m && styles.filterTabGbcActive]}
            onPress={() => onSetFeedMode(m)}
          >
            <Text style={[styles.filterTabTextGbc, feedMode === m && styles.filterTabTextGbcActive]}>
              {m === 'upcoming' ? '📋 UPCOMING' : '📜 HISTORICAL'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Category Header */}
      {selectedCategory && (
        <View style={styles.categoryHeader}>
          <Text style={styles.categoryHeaderIcon}>{selectedCategory.icon}</Text>
          <Text style={styles.categoryHeaderText}>{selectedCategory.name.toUpperCase()}</Text>
        </View>
      )}

      {/* Progress Bar - shows voted vs total outstanding */}
      <View style={styles.progressBarContainer}>
        <Text style={styles.progressLabel}>PROGRESS</Text>
        <View style={styles.progressBarOuter}>
          <View
            style={[
              styles.progressBarInner,
              { width: `${(votesCount + totalRemaining) > 0 ? (votesCount / (votesCount + totalRemaining)) * 100 : 0}%` }
            ]}
          />
        </View>
        <Text style={styles.progressText}>{totalRemaining} remaining</Text>
      </View>

      {/* Vote Counter */}
      <View style={styles.voteCounter}>
        <Text style={styles.voteCounterText}>VOTES: {votesCount}</Text>
      </View>

      {currentMeasure ? (
        <SwipeCard measure={currentMeasure} onVote={handleVote} />
      ) : isFetchingMore ? (
        /* Loading next batch */
        <View style={styles.gbcLoadingContainer}>
          <Text style={styles.loadingPixel}>Loading more bills...</Text>
          <View style={styles.pixelLoader}>
            <Text style={styles.loaderDot}>●</Text>
            <Text style={styles.loaderDot}>●</Text>
            <Text style={styles.loaderDot}>●</Text>
          </View>
        </View>
      ) : selectedCategory && totalRemaining === 0 ? (
        /* Category Complete Screen */
        <PixelBox variant="dialog" style={styles.victoryBox}>
          <Text style={styles.victorySprite}>{selectedCategory.icon}</Text>
          <Text style={styles.victoryTitle}>CATEGORY COMPLETE!</Text>
          <Text style={styles.victoryText}>{selectedCategory.name}</Text>
          <Text style={styles.victoryStats}>Votes cast: {votesCount}</Text>
          <View style={styles.categoryCompleteButtons}>
            <PixelButton
              onPress={() => { onClearCategory(); }}
              title="KEEP VOTING"
              variant="primary"
              icon="▶"
            />
            <PixelButton
              onPress={() => onNavigate('home', { scrollToCategories: true })}
              title="CHOOSE CATEGORY"
              variant="secondary"
              icon="◄"
            />
          </View>
        </PixelBox>
      ) : totalRemaining === 0 ? (
        /* General Complete Screen — all bills voted on */
        <PixelBox variant="dialog" style={styles.victoryBox}>
          <Text style={styles.victorySprite}>🎉</Text>
          <Text style={styles.victoryTitle}>QUEST COMPLETE!</Text>
          <Text style={styles.victoryText}>You reviewed all available bills!</Text>
          <Text style={styles.victoryStats}>Votes cast: {votesCount}</Text>
          <PixelButton onPress={() => onNavigate('home')} title="RETURN" variant="primary" icon="◄" />
        </PixelBox>
      ) : (
        /* End of current batch but more exist — trigger fetch */
        <View style={styles.gbcLoadingContainer}>
          <Text style={styles.loadingPixel}>Loading more bills...</Text>
          <View style={styles.pixelLoader}>
            <Text style={styles.loaderDot}>●</Text>
            <Text style={styles.loaderDot}>●</Text>
            <Text style={styles.loaderDot}>●</Text>
          </View>
        </View>
      )}
    </View>
  );
}

// Settings Screen
function SettingsScreen({ user, onNavigate, onUpdateUser }: {
  user: User;
  onNavigate: (screen: string, options?: { scrollToCategories?: boolean }) => void;
  onUpdateUser: (user: User) => void;
}) {
  // Profile field state
  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [email, setEmail] = useState(user.email);
  const [birthday, setBirthday] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [showPasswordField, setShowPasswordField] = useState(false);

  // Address state
  const [savedAddr, setSavedAddr] = useState<{ city: string; state: string; zip: string } | null>(null);

  // Address modal state (reuse HomeScreen pattern)
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [addrStreet, setAddrStreet] = useState('');
  const [addrCity, setAddrCity] = useState('');
  const [addrState, setAddrState] = useState('');
  const [addrZip, setAddrZip] = useState('');
  const [addrSuggestions, setAddrSuggestions] = useState<{ matchedAddress: string; coordinates: { x: number; y: number }; addressComponents: any }[]>([]);
  const [addrSaving, setAddrSaving] = useState(false);
  const [addrError, setAddrError] = useState('');
  const addrDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track original email to detect changes
  const originalEmail = useRef(user.email);

  useEffect(() => { loadProfile(); }, []);

  // Show password field when email changes
  useEffect(() => {
    setShowPasswordField(email !== originalEmail.current);
    if (email === originalEmail.current) setCurrentPassword('');
  }, [email]);

  const loadProfile = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/me`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setFirstName(data.user.first_name || '');
        setLastName(data.user.last_name || '');
        setEmail(data.user.email || '');
        originalEmail.current = data.user.email || '';

        // Convert birthday from YYYY-MM-DD to MM-DD-YYYY
        if (data.user.birthday) {
          const [y, m, d] = data.user.birthday.split('-');
          setBirthday(`${m}-${d}-${y}`);
        }

        if (data.address && data.address.city) {
          setSavedAddr({
            city: data.address.city,
            state: data.address.state || '',
            zip: data.address.postal_code || '',
          });
        }
      }
    } catch (err) {
      setError('Failed to load profile');
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-format birthday as MM-DD-YYYY (same as LoginScreen)
  const handleBirthdayChange = (text: string) => {
    const numbers = text.replace(/[^0-9]/g, '');
    let formatted = '';
    if (numbers.length > 0) formatted = numbers.substring(0, 2);
    if (numbers.length > 2) formatted += '-' + numbers.substring(2, 4);
    if (numbers.length > 4) formatted += '-' + numbers.substring(4, 8);
    setBirthday(formatted);
  };

  const handleSaveProfile = async () => {
    setError('');
    setSuccessMsg('');

    // Validate name fields
    if (!firstName.trim()) { setError('First name is required'); return; }
    if (!lastName.trim()) { setError('Last name is required'); return; }

    // Validate birthday if provided
    if (birthday) {
      const parts = birthday.split('-');
      if (parts.length !== 3 || parts[0].length !== 2 || parts[1].length !== 2 || parts[2].length !== 4) {
        setError('Invalid birthday format (use MM-DD-YYYY)'); return;
      }
      const [m, d, y] = parts;
      const bDate = new Date(`${y}-${m}-${d}`);
      if (isNaN(bDate.getTime())) { setError('Invalid birthday'); return; }
      const age = new Date().getFullYear() - bDate.getFullYear();
      if (age < 13) { setError('Must be at least 13 years old'); return; }
      if (age > 120) { setError('Invalid birthday'); return; }
    }

    // Require password if email changed
    if (email !== originalEmail.current && !currentPassword) {
      setError('Current password is required to change email'); return;
    }

    setIsSaving(true);
    try {
      const body: any = {};
      if (firstName.trim() !== user.first_name) body.first_name = firstName.trim();
      if (lastName.trim() !== user.last_name) body.last_name = lastName.trim();
      if (email !== originalEmail.current) {
        body.email = email;
        body.current_password = currentPassword;
      }
      if (birthday) {
        const [m, d, y] = birthday.split('-');
        body.birthday = `${y}-${m}-${d}`;
      }

      // Only call API if something changed
      if (Object.keys(body).length === 0) {
        setSuccessMsg('No changes to save');
        setIsSaving(false);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/me/profile`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'Failed to update profile' }));
        if (Array.isArray(errData.detail)) {
          throw new Error(errData.detail.map((e: any) => e.msg).join(', '));
        }
        throw new Error(errData.detail || 'Failed to update profile');
      }

      const data = await response.json();

      // Update local user state
      onUpdateUser({
        ...user,
        first_name: data.user.first_name,
        last_name: data.user.last_name,
        email: data.user.email,
        birthday: data.user.birthday,
      });

      originalEmail.current = data.user.email;
      setCurrentPassword('');
      setShowPasswordField(false);
      setSuccessMsg('Profile updated!');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  // Address functions (same pattern as HomeScreen)
  const openAddressModal = () => {
    setAddrError('');
    setAddrSuggestions([]);
    if (savedAddr) {
      setAddrStreet('');
      setAddrCity(savedAddr.city);
      setAddrState(savedAddr.state);
      setAddrZip(savedAddr.zip);
    } else {
      setAddrStreet('');
      setAddrCity('');
      setAddrState('');
      setAddrZip('');
    }
    setShowAddressModal(true);
  };

  const searchAddress = (street: string) => {
    setAddrStreet(street);
    if (addrDebounceRef.current) clearTimeout(addrDebounceRef.current);
    if (street.length < 5) { setAddrSuggestions([]); return; }
    addrDebounceRef.current = setTimeout(async () => {
      try {
        const onelineAddr = `${street}, ${addrCity || ''}, ${addrState || ''} ${addrZip || ''}`.trim();
        const url = `https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encodeURIComponent(onelineAddr)}&benchmark=Public_AR_Current&format=json`;
        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          const matches = data?.result?.addressMatches || [];
          setAddrSuggestions(matches.slice(0, 5));
        }
      } catch (err) { console.error('Address search failed:', err); }
    }, 400);
  };

  const selectSuggestion = (suggestion: any) => {
    const components = suggestion.addressComponents || {};
    setAddrStreet(suggestion.matchedAddress?.split(',')[0] || addrStreet);
    setAddrCity(components.city || addrCity);
    setAddrState(components.state || addrState);
    setAddrZip(components.zip || addrZip);
    setAddrSuggestions([]);
  };

  const saveAddress = async () => {
    if (!addrStreet || !addrCity || !addrState || !addrZip) return;
    setAddrSaving(true);
    setAddrError('');
    try {
      const response = await fetch(`${API_BASE_URL}/me/address`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          line1: addrStreet,
          city: addrCity,
          state: addrState,
          postal_code: addrZip,
          country: 'US',
        }),
      });
      if (response.ok) {
        setSavedAddr({ city: addrCity, state: addrState, zip: addrZip });
        setShowAddressModal(false);
        setSuccessMsg('Address updated!');
        setTimeout(() => setSuccessMsg(''), 3000);
      } else {
        const data = await response.json().catch(() => null);
        setAddrError(data?.detail || 'Failed to save address. Please try again.');
      }
    } catch (err) {
      setAddrError('Network error. Please check your connection.');
    } finally {
      setAddrSaving(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.gbcLoadingContainer}>
        <Text style={styles.loadingPixel}>Loading...</Text>
        <View style={styles.pixelLoader}>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: GBC.screenBg }}
      contentContainerStyle={{ padding: 12 }}
      keyboardShouldPersistTaps="handled"
    >
      {/* Header */}
      <Text style={[styles.boxTitle, { color: GBC.yellow, marginBottom: 16 }]}>═══ SETTINGS ═══</Text>

      {/* Profile Section */}
      <PixelBox variant="menu" style={{ marginBottom: 12 }}>
        <Text style={styles.boxTitle}>PROFILE</Text>

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>FIRST NAME:</Text>
          <TextInput
            style={styles.pixelInput}
            value={firstName}
            onChangeText={setFirstName}
            placeholder="First"
            placeholderTextColor={GBC.lightGray}
          />
        </View>

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>LAST NAME:</Text>
          <TextInput
            style={styles.pixelInput}
            value={lastName}
            onChangeText={setLastName}
            placeholder="Last"
            placeholderTextColor={GBC.lightGray}
          />
        </View>

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>BIRTHDAY:</Text>
          <TextInput
            style={styles.pixelInput}
            placeholder="MM-DD-YYYY"
            value={birthday}
            onChangeText={handleBirthdayChange}
            placeholderTextColor={GBC.lightGray}
            keyboardType="number-pad"
            maxLength={10}
          />
        </View>
      </PixelBox>

      {/* Email Section */}
      <PixelBox variant="dialog" style={{ marginBottom: 12 }}>
        <Text style={styles.boxTitle}>EMAIL</Text>

        <View style={styles.inputRow}>
          <Text style={styles.inputLabel}>EMAIL:</Text>
          <TextInput
            style={styles.pixelInput}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            placeholder="you@email.com"
            placeholderTextColor={GBC.lightGray}
          />
        </View>

        {showPasswordField && (
          <View style={styles.inputRow}>
            <Text style={[styles.inputLabel, { color: GBC.red }]}>CURRENT PASSWORD:</Text>
            <TextInput
              style={[styles.pixelInput, { borderColor: GBC.red }]}
              placeholder="Required to change email"
              value={currentPassword}
              onChangeText={setCurrentPassword}
              secureTextEntry
              placeholderTextColor={GBC.lightGray}
            />
            <Text style={styles.addressHint}>Password required for security</Text>
          </View>
        )}
      </PixelBox>

      {/* Address Section */}
      <PixelBox variant="dialog" style={{ marginBottom: 12 }}>
        <Text style={styles.boxTitle}>ADDRESS</Text>
        {savedAddr ? (
          <View style={{ alignItems: 'center' }}>
            <Text style={styles.settingsAddrText}>
              {savedAddr.city}, {savedAddr.state} {savedAddr.zip}
            </Text>
            <TouchableOpacity style={{ paddingVertical: 8 }} onPress={openAddressModal}>
              <Text style={styles.settingsAddrLink}>UPDATE ADDRESS</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableOpacity style={{ paddingVertical: 12, alignItems: 'center' }} onPress={openAddressModal}>
            <Text style={styles.settingsAddrLink}>+ ADD ADDRESS</Text>
          </TouchableOpacity>
        )}
      </PixelBox>

      {/* Error / Success Messages */}
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorPixelText}>⚠ {error}</Text>
        </View>
      ) : null}

      {successMsg ? (
        <View style={[styles.errorBox, { backgroundColor: '#2e8b57', borderColor: '#1a6b3a' }]}>
          <Text style={styles.errorPixelText}>✓ {successMsg}</Text>
        </View>
      ) : null}

      {/* Save Button */}
      <View style={styles.buttonRow}>
        <PixelButton
          onPress={handleSaveProfile}
          title={isSaving ? 'SAVING...' : 'SAVE CHANGES'}
          variant="primary"
          disabled={isSaving}
          icon="💾"
        />
      </View>

      {/* Back Button */}
      <View style={{ marginTop: 12 }}>
        <PixelButton
          onPress={() => onNavigate('home')}
          title="BACK"
          variant="secondary"
          icon="◄"
        />
      </View>

      {/* Address Modal */}
      <Modal visible={showAddressModal} animationType="slide" transparent>
        <View style={styles.addrModalOverlay}>
          <View style={styles.addrModalContainer}>
            <PixelBox variant="dialog" style={styles.addrModalBox}>
              <Text style={styles.boxTitle}>{savedAddr ? '═══ UPDATE ADDRESS ═══' : '═══ ENTER ADDRESS ═══'}</Text>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>STREET:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="123 Main St"
                  value={addrStreet}
                  onChangeText={searchAddress}
                  placeholderTextColor={GBC.lightGray}
                  autoFocus
                />
              </View>

              {addrSuggestions.length > 0 && (
                <View style={styles.addrSuggestions}>
                  {addrSuggestions.map((s, i) => (
                    <TouchableOpacity
                      key={i}
                      style={styles.addrSuggestionItem}
                      onPress={() => selectSuggestion(s)}
                    >
                      <Text style={styles.addrSuggestionText} numberOfLines={1}>
                        {s.matchedAddress}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>CITY:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="Phoenix"
                  value={addrCity}
                  onChangeText={setAddrCity}
                  placeholderTextColor={GBC.lightGray}
                />
              </View>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>STATE:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="AZ"
                  value={addrState}
                  onChangeText={(t) => setAddrState(t.toUpperCase().slice(0, 2))}
                  placeholderTextColor={GBC.lightGray}
                  autoCapitalize="characters"
                  maxLength={2}
                />
              </View>

              <View style={styles.addrField}>
                <Text style={styles.addrFieldLabel}>ZIP:</Text>
                <TextInput
                  style={styles.addrInput}
                  placeholder="85001"
                  value={addrZip}
                  onChangeText={setAddrZip}
                  placeholderTextColor={GBC.lightGray}
                  keyboardType="number-pad"
                />
              </View>

              {addrError ? (
                <Text style={styles.addrErrorText}>{addrError}</Text>
              ) : null}

              <View style={styles.addrButtonRow}>
                <TouchableOpacity
                  style={styles.addrCancelButton}
                  onPress={() => { setShowAddressModal(false); setAddrSuggestions([]); setAddrError(''); }}
                >
                  <Text style={styles.addrCancelText}>CANCEL</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.addrSaveButton, (!addrStreet || !addrCity || !addrState || !addrZip) && { opacity: 0.5 }]}
                  onPress={saveAddress}
                  disabled={!addrStreet || !addrCity || !addrState || !addrZip || addrSaving}
                >
                  <Text style={styles.addrSaveText}>{addrSaving ? 'SAVING...' : 'SAVE'}</Text>
                </TouchableOpacity>
              </View>
            </PixelBox>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

// Main App with Navigation - Pokemon Style
function MainApp({ user, onLogout, onUpdateUser }: { user: User; onLogout: () => void; onUpdateUser: (user: User) => void }) {
  const [currentScreen, setCurrentScreen] = useState('home');
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [scrollToCategories, setScrollToCategories] = useState(false);
  const [feedMode, setFeedMode] = useState<'upcoming' | 'historical'>('upcoming');
  const slideAnim = useRef(new Animated.Value(300)).current;

  const openMenu = () => {
    setMenuOpen(true);
    Animated.timing(slideAnim, {
      toValue: 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  };

  const closeMenu = () => {
    Animated.timing(slideAnim, {
      toValue: 300,
      duration: 200,
      useNativeDriver: true,
    }).start(() => setMenuOpen(false));
  };

  const handleMenuNavigate = (screen: string) => {
    closeMenu();
    setScrollToCategories(false);
    setTimeout(() => setCurrentScreen(screen), 100);
  };

  const handleLogout = () => {
    closeMenu();
    setTimeout(() => onLogout(), 100);
  };

  const handleSelectCategory = (category: Category | null) => {
    setSelectedCategory(category);
    setScrollToCategories(false); // Reset scroll flag when selecting a category
  };

  const handleClearCategory = () => {
    setSelectedCategory(null);
    // Reload the feed with all bills
  };

  const handleNavigate = (screen: string, options?: { scrollToCategories?: boolean }) => {
    if (options?.scrollToCategories) {
      setScrollToCategories(true);
    } else {
      setScrollToCategories(false);
    }
    setCurrentScreen(screen);
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'home':
        return <HomeScreen user={user} onNavigate={handleNavigate} onSelectCategory={handleSelectCategory} scrollToCategories={scrollToCategories} feedMode={feedMode} onSetFeedMode={setFeedMode} />;
      case 'feed':
        return <FeedScreen user={user} onNavigate={handleNavigate} selectedCategory={selectedCategory} onClearCategory={handleClearCategory} feedMode={feedMode} onSetFeedMode={setFeedMode} />;
      case 'history':
        return <HistoryScreen user={user} onNavigate={handleNavigate} />;
      case 'settings':
        return <SettingsScreen user={user} onNavigate={handleNavigate} onUpdateUser={onUpdateUser} />;
      default:
        return <HomeScreen user={user} onNavigate={handleNavigate} onSelectCategory={handleSelectCategory} scrollToCategories={scrollToCategories} feedMode={feedMode} onSetFeedMode={setFeedMode} />;
    }
  };

  return (
    <View style={styles.gbcMainContainer}>
      {/* Top Bar - Pokemon style header */}
      <View style={styles.gbcHeader}>
        <TouchableOpacity onPress={() => { setScrollToCategories(false); setCurrentScreen('home'); }}>
          <Text style={styles.gbcHeaderTitle}>🏘️ VILLAGEVOTE</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={openMenu} style={styles.hamburgerButton}>
          <Text style={styles.hamburgerIcon}>☰</Text>
        </TouchableOpacity>
      </View>

      {/* Main Content */}
      <View style={styles.gbcContent}>
        {renderScreen()}
      </View>

      {/* Bottom Tab Bar - Pokemon menu style */}
      <View style={styles.gbcTabBar}>
        <TouchableOpacity
          style={[styles.gbcTab, currentScreen === 'home' && styles.gbcTabActive]}
          onPress={() => { setScrollToCategories(false); setCurrentScreen('home'); }}
        >
          <Text style={styles.gbcTabIcon}>🏠</Text>
          <Text style={[styles.gbcTabLabel, currentScreen === 'home' && styles.gbcTabLabelActive]}>HOME</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.gbcTab, currentScreen === 'feed' && styles.gbcTabActive]}
          onPress={() => { setScrollToCategories(false); setCurrentScreen('feed'); }}
        >
          <Text style={styles.gbcTabIcon}>🗳️</Text>
          <Text style={[styles.gbcTabLabel, currentScreen === 'feed' && styles.gbcTabLabelActive]}>VOTE</Text>
        </TouchableOpacity>
      </View>

      {/* Slide-out Menu */}
      {menuOpen && (
        <View style={styles.menuOverlay}>
          <TouchableOpacity style={styles.menuBackdrop} onPress={closeMenu} activeOpacity={1} />
          <Animated.View style={[styles.slideMenu, { transform: [{ translateX: slideAnim }] }]}>
            <View style={styles.menuHeader}>
              <Text style={styles.menuHeaderText}>═══ MENU ═══</Text>
              <TouchableOpacity onPress={closeMenu}>
                <Text style={styles.menuCloseBtn}>✕</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.menuUserInfo}>
              <Text style={styles.menuUserSprite}>👤</Text>
              <Text style={styles.menuUserName}>{user.first_name.toUpperCase()}</Text>
            </View>

            <View style={styles.menuDivider} />

            <TouchableOpacity style={styles.slideMenuItem} onPress={() => handleMenuNavigate('history')}>
              <Text style={styles.slideMenuIcon}>📜</Text>
              <Text style={styles.slideMenuText}>VOTE HISTORY</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.slideMenuItem} onPress={() => handleMenuNavigate('settings')}>
              <Text style={styles.slideMenuIcon}>⚙️</Text>
              <Text style={styles.slideMenuText}>SETTINGS</Text>
            </TouchableOpacity>

            <View style={styles.menuDivider} />

            <TouchableOpacity style={[styles.slideMenuItem, styles.logoutMenuItem]} onPress={handleLogout}>
              <Text style={styles.slideMenuIcon}>🚪</Text>
              <Text style={styles.logoutMenuText}>LOGOUT</Text>
            </TouchableOpacity>
          </Animated.View>
        </View>
      )}
    </View>
  );
}

// Root App Component
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: try to restore session from secure storage
  useEffect(() => {
    (async () => {
      try {
        const saved = await loadSession();
        if (saved?.access_token) {
          // Validate the token is still good by hitting /me
          const res = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer ${saved.access_token}` },
          });
          if (res.ok) {
            setUser(saved);
          } else {
            await clearSession();
          }
        }
      } catch { /* no saved session */ }
      setIsLoading(false);
    })();
  }, []);

  // Save session to secure storage when user logs in
  const handleLogin = useCallback(async (u: User) => {
    setUser(u);
    await saveSession(u);
  }, []);

  // Clear secure storage on logout
  const handleLogout = useCallback(async () => {
    setUser(null);
    await clearSession();
  }, []);

  // Update user and persist
  const handleUpdateUser = useCallback(async (u: User) => {
    setUser(u);
    await saveSession(u);
  }, []);

  if (isLoading) {
    return (
      <View style={styles.splashScreen}>
        <Text style={styles.splashLogo}>🏘️</Text>
        <Text style={styles.splashTitle}>VILLAGEVOTE</Text>
        <Text style={styles.splashSubtitle}>By the People. For your People.</Text>
        <View style={styles.pixelLoader}>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
          <Text style={styles.loaderDot}>●</Text>
        </View>
        <Text style={styles.splashPress}>Press START</Text>
      </View>
    );
  }

  return (
    <View style={styles.gbcFrame}>
      <StatusBar style="light" />
      {user ? <MainApp user={user} onLogout={handleLogout} onUpdateUser={handleUpdateUser} /> : <LoginScreen onLogin={handleLogin} />}
    </View>
  );
}

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const styles = StyleSheet.create({
  // GBC Frame & Container
  gbcFrame: {
    flex: 1,
    backgroundColor: GBC.darkBlue,
  },
  gbcContainer: {
    flex: 1,
    backgroundColor: GBC.white,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gbcMainContainer: {
    flex: 1,
    backgroundColor: GBC.screenBg,
  },
  gbcScrollView: {
    flex: 1,
    padding: 12,
    backgroundColor: GBC.screenBg,
  },
  gbcContent: {
    flex: 1,
  },

  // Splash Screen
  splashScreen: {
    flex: 1,
    backgroundColor: GBC.blue,
    alignItems: 'center',
    justifyContent: 'center',
  },
  splashLogo: {
    fontSize: 80,
    marginBottom: 16,
  },
  splashTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: GBC.lighterGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    letterSpacing: 4,
  },
  splashSubtitle: {
    fontSize: 14,
    color: GBC.yellow,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginTop: 8,
    letterSpacing: 2,
  },
  splashPress: {
    fontSize: 16,
    color: GBC.lighterGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginTop: 40,
    opacity: 0.8,
  },

  // Pixel Loader
  pixelLoader: {
    flexDirection: 'row',
    marginTop: 24,
    gap: 8,
  },
  loaderDot: {
    fontSize: 16,
    color: GBC.lighterGreen,
  },

  // Login Title
  titleBanner: {
    alignItems: 'center',
    marginBottom: 24,
  },
  titlePixelArt: {
    fontSize: 64,
    marginBottom: 8,
  },
  gameTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    letterSpacing: 4,
  },
  titleSubtext: {
    fontSize: 12,
    color: GBC.yellow,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginTop: 4,
  },

  // Pixel Box
  pixelBox: {
    borderWidth: 4,
    borderRadius: 0,
    padding: 4,
    shadowColor: GBC.black,
    shadowOffset: { width: 4, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 0,
    elevation: 4,
  },
  pixelBoxInner: {
    borderWidth: 2,
    borderColor: 'rgba(0,0,0,0.1)',
    padding: 12,
  },

  // Login Box
  loginBox: {
    width: '100%',
    maxWidth: 360,
    marginBottom: 40,
  },
  menuTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 16,
    textAlign: 'center',
  },

  // Input Styles
  inputRow: {
    marginBottom: 12,
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 4,
  },
  pixelInput: {
    backgroundColor: GBC.white,
    borderWidth: 3,
    borderColor: GBC.blue,
    borderRadius: 0,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    color: GBC.black,
  },

  // Pixel Button
  pixelButton: {
    borderWidth: 4,
    borderRadius: 0,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    shadowColor: GBC.black,
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 0,
    elevation: 3,
  },
  pixelButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    letterSpacing: 2,
  },

  // Button Row
  buttonRow: {
    marginTop: 16,
  },

  // Error Box
  errorBox: {
    backgroundColor: GBC.red,
    borderWidth: 2,
    borderColor: GBC.darkRed,
    padding: 8,
    marginVertical: 8,
  },
  errorPixelText: {
    color: GBC.white,
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
  },

  // Switch Button
  switchButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  switchText: {
    color: GBC.yellow,
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // State selector styles
  stateText: {
    color: GBC.darkGreen,
    fontSize: 14,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  statePlaceholder: {
    color: GBC.lightGray,
    fontSize: 14,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  addressToggle: {
    paddingVertical: 8,
    marginTop: 8,
  },
  addressToggleText: {
    color: GBC.yellow,
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
  },
  addressHint: {
    color: GBC.lightGray,
    fontSize: 11,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontStyle: 'italic',
    marginBottom: 8,
    lineHeight: 16,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stateModal: {
    width: '85%',
    height: '60%',
    backgroundColor: GBC.cream,
    borderWidth: 4,
    borderColor: GBC.blue,
  },
  stateModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 3,
    borderBottomColor: GBC.tan,
    backgroundColor: GBC.blue,
  },
  stateModalTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  stateModalClose: {
    fontSize: 18,
    color: GBC.white,
    fontWeight: 'bold',
  },
  stateList: {
    flex: 1,
  },
  stateItem: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: GBC.tan,
  },
  stateItemSelected: {
    backgroundColor: GBC.yellow,
  },
  stateItemText: {
    fontSize: 14,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  stateItemTextSelected: {
    fontWeight: 'bold',
  },

  // State dropdown (inline autocomplete)
  stateDropdown: {
    backgroundColor: GBC.cream,
    borderWidth: 2,
    borderColor: GBC.blue,
    borderTopWidth: 0,
    marginTop: -8,
    marginBottom: 8,
    maxHeight: 150,
  },
  stateDropdownItem: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: GBC.tan,
  },
  stateDropdownText: {
    fontSize: 13,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Version Text
  versionText: {
    position: 'absolute',
    bottom: 20,
    fontSize: 10,
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  versionTextStatic: {
    fontSize: 10,
    color: GBC.lightGray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
    marginTop: 16,
    paddingBottom: 30,
  },
  loginScrollView: {
    flex: 1,
    backgroundColor: GBC.darkBlue,
  },
  loginScrollContent: {
    flexGrow: 1,
    padding: 16,
    paddingBottom: 40,
    alignItems: 'center',
  },

  // Header
  gbcHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'ios' ? 50 : 30,
    paddingBottom: 12,
    backgroundColor: GBC.blue,
    borderBottomWidth: 4,
    borderBottomColor: GBC.darkBlue,
  },
  gbcHeaderTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    letterSpacing: 2,
  },
  logoutButton: {
    backgroundColor: GBC.red,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 2,
    borderColor: GBC.darkRed,
  },
  logoutButtonText: {
    color: GBC.white,
    fontSize: 12,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Hamburger Menu Button
  hamburgerButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  hamburgerIcon: {
    color: GBC.white,
    fontSize: 24,
    fontWeight: 'bold',
  },

  // Slide-out Menu
  menuOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 100,
  },
  menuBackdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  slideMenu: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: 260,
    backgroundColor: GBC.white,
    borderLeftWidth: 4,
    borderLeftColor: GBC.blue,
    paddingTop: Platform.OS === 'ios' ? 50 : 10,
  },
  menuHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 3,
    borderBottomColor: GBC.tan,
  },
  menuHeaderText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  menuCloseBtn: {
    fontSize: 20,
    color: GBC.darkGreen,
    fontWeight: 'bold',
  },
  menuUserInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: GBC.tan,
  },
  menuUserSprite: {
    fontSize: 32,
    marginRight: 12,
  },
  menuUserName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  menuDivider: {
    height: 3,
    backgroundColor: GBC.tan,
    marginVertical: 8,
  },
  slideMenuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  slideMenuIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  slideMenuText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  slideMenuItemDisabled: {
    opacity: 0.5,
  },
  slideMenuTextDisabled: {
    color: GBC.gray,
  },
  logoutMenuItem: {
    marginTop: 'auto',
    backgroundColor: GBC.red,
    marginHorizontal: 16,
    marginBottom: 30,
    borderWidth: 3,
    borderColor: GBC.darkRed,
    justifyContent: 'center',
  },
  logoutMenuText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Tab Bar
  gbcTabBar: {
    flexDirection: 'row',
    backgroundColor: GBC.darkBlue,
    borderTopWidth: 4,
    borderTopColor: GBC.blue,
    paddingBottom: Platform.OS === 'ios' ? 20 : 8,
  },
  gbcTab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
  },
  gbcTabActive: {
    backgroundColor: GBC.blue,
  },
  gbcTabIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  gbcTabLabel: {
    fontSize: 10,
    color: GBC.lightGray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
  },
  gbcTabLabelActive: {
    color: GBC.yellow,
  },

  // Loading
  gbcLoadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: GBC.screenBg,
  },
  loadingPixel: {
    fontSize: 18,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
  },

  // Trainer Card
  trainerCard: {
    marginBottom: 12,
  },
  trainerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  trainerSprite: {
    fontSize: 48,
    marginRight: 16,
  },
  trainerInfo: {
    flex: 1,
  },
  trainerName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  trainerTitle: {
    fontSize: 12,
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Stats Box
  statsBox: {
    marginBottom: 12,
  },
  boxTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
    marginBottom: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statDisplay: {
    width: '48%',
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    backgroundColor: GBC.tan,
    padding: 8,
    borderWidth: 2,
    borderColor: GBC.darkTan,
  },
  statIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  statInfo: {
    flex: 1,
  },
  statLabel: {
    fontSize: 10,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  statValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  dividerPixel: {
    height: 2,
    backgroundColor: GBC.darkTan,
    marginVertical: 12,
  },

  // Category Selection
  categoryBox: {
    marginBottom: 12,
  },
  feedModeToggle: {
    flexDirection: 'row',
    marginBottom: 12,
    gap: 8,
  },
  feedModeBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: GBC.tan,
    borderWidth: 3,
    borderColor: GBC.darkTan,
  },
  feedModeBtnActive: {
    backgroundColor: GBC.blue,
    borderColor: GBC.darkBlue,
  },
  feedModeBtnText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  feedModeBtnTextActive: {
    color: GBC.white,
  },
  allBillsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GBC.blue,
    padding: 12,
    marginBottom: 12,
    borderWidth: 3,
    borderColor: GBC.darkBlue,
  },
  allBillsIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  allBillsText: {
    flex: 1,
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  allBillsArrow: {
    fontSize: 16,
    color: GBC.yellow,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  categoryButton: {
    width: '48%',
    backgroundColor: GBC.tan,
    padding: 10,
    marginBottom: 8,
    borderWidth: 2,
    borderColor: GBC.darkTan,
    alignItems: 'center',
  },
  categoryIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  categoryName: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
  },
  categoryCount: {
    fontSize: 12,
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginTop: 2,
  },
  categoryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: GBC.yellow,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderBottomWidth: 3,
    borderBottomColor: GBC.darkYellow,
  },
  categoryHeaderIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  categoryHeaderText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.black,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Menu Box
  menuBox: {
    marginBottom: 12,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 2,
    borderBottomColor: GBC.tan,
  },
  menuItemDisabled: {
    opacity: 0.5,
  },
  menuArrow: {
    fontSize: 16,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginRight: 12,
  },
  menuItemText: {
    flex: 1,
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  menuTextDisabled: {
    color: GBC.gray,
  },
  menuItemIcon: {
    fontSize: 20,
  },

  // Feed Screen
  feedGbcContainer: {
    flex: 1,
    backgroundColor: GBC.screenBg,
  },
  progressBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: GBC.blue,
    borderBottomWidth: 4,
    borderBottomColor: GBC.darkBlue,
  },
  progressLabel: {
    fontSize: 10,
    color: GBC.yellow,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginRight: 8,
  },
  progressBarOuter: {
    flex: 1,
    height: 12,
    backgroundColor: GBC.darkBlue,
    borderWidth: 2,
    borderColor: GBC.white,
  },
  progressBarInner: {
    height: '100%',
    backgroundColor: GBC.yellow,
  },
  progressText: {
    fontSize: 10,
    color: GBC.yellow,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  voteCounter: {
    backgroundColor: GBC.yellow,
    paddingVertical: 6,
    paddingHorizontal: 16,
    alignSelf: 'center',
    marginTop: 8,
    borderWidth: 2,
    borderColor: GBC.darkYellow,
  },
  voteCounterText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.black,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Battle Container
  battleContainer: {
    flex: 1,
    padding: 12,
    justifyContent: 'space-between',
  },

  // Bill Card
  billCard: {
    flex: 1,
    marginBottom: 12,
  },
  billHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  typeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderWidth: 2,
    borderColor: GBC.black,
  },
  typeBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  skippedBadgeGbc: {
    backgroundColor: GBC.yellow,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 2,
    borderColor: GBC.darkYellow,
  },
  skippedBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.black,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  outcomeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 2,
    borderColor: GBC.black,
  },
  outcomeBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  billName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 12,
    lineHeight: 24,
  },
  statusBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  statusLabel: {
    fontSize: 10,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginRight: 8,
  },
  statusBar: {
    flex: 1,
    backgroundColor: GBC.tan,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderWidth: 2,
    borderColor: GBC.darkTan,
  },
  statusValue: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  descriptionBox: {
    flex: 1,
    backgroundColor: GBC.cream,
    borderWidth: 3,
    borderColor: GBC.blue,
    padding: 12,
    minHeight: 180,
  },
  descriptionScroll: {
    flex: 1,
  },
  descriptionText: {
    fontSize: 13,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    lineHeight: 20,
  },

  // Battle Menu
  battleMenu: {
    minHeight: 100,
  },
  battlePrompt: {
    fontSize: 12,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginBottom: 8,
  },
  battleOptions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  battleOption: {
    width: '48%',
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: GBC.black,
  },
  yeaOption: {
    backgroundColor: '#2e8b57',  // Sea green for YEA votes
  },
  nayOption: {
    backgroundColor: GBC.red,
  },
  skipOption: {
    backgroundColor: GBC.tan,
  },
  infoOption: {
    backgroundColor: GBC.white,
  },
  battleOptionText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Victory Box
  victoryBox: {
    margin: 20,
    alignItems: 'center',
    padding: 24,
  },
  victorySprite: {
    fontSize: 64,
    marginBottom: 16,
  },
  victoryTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 8,
  },
  victoryText: {
    fontSize: 14,
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
    marginBottom: 8,
  },
  victoryStats: {
    fontSize: 16,
    fontWeight: 'bold',
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 16,
  },
  categoryCompleteButtons: {
    width: '100%',
    gap: 12,
  },

  // History Screen
  historyGbcContainer: {
    flex: 1,
    backgroundColor: GBC.screenBg,
  },
  filterTabsGbc: {
    flexDirection: 'row',
    backgroundColor: GBC.blue,
    borderBottomWidth: 4,
    borderBottomColor: GBC.darkBlue,
    paddingVertical: 8,
    paddingHorizontal: 4,
  },
  filterTabGbc: {
    flex: 1,
    paddingVertical: 8,
    marginHorizontal: 4,
    alignItems: 'center',
    backgroundColor: GBC.tan,
    borderWidth: 2,
    borderColor: GBC.darkTan,
  },
  filterTabGbcActive: {
    backgroundColor: GBC.darkGreen,
    borderColor: GBC.black,
  },
  filterTabTextGbc: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  filterTabTextGbcActive: {
    color: GBC.lighterGreen,
  },
  historyListGbc: {
    flex: 1,
    padding: 12,
  },
  historyItemGbc: {
    marginBottom: 12,
  },
  historyItemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  historyItemNumber: {
    fontSize: 12,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    marginRight: 8,
  },
  levelBadgeGbc: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 2,
    borderColor: GBC.black,
    marginRight: 8,
  },
  levelBadgeTextGbc: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.white,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  historyOutcomeSprite: {
    fontSize: 16,
    marginLeft: 'auto',
  },
  historyItemTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 8,
    lineHeight: 20,
  },
  historyItemSummary: {
    fontSize: 12,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 8,
    lineHeight: 16,
  },
  historyItemFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 2,
    borderTopColor: GBC.tan,
    paddingTop: 8,
  },
  voteIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  voteLabel: {
    fontSize: 10,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginRight: 4,
  },
  voteValue: {
    fontSize: 12,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  outcomeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  emptyHistoryBox: {
    margin: 20,
    alignItems: 'center',
    padding: 24,
  },
  emptyHistoryText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 8,
  },
  emptyHistorySubtext: {
    fontSize: 12,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
    marginBottom: 16,
  },

  // Representatives Section
  repsBox: {
    marginBottom: 12,
  },
  repsEmpty: {
    alignItems: 'center',
    padding: 16,
  },
  repsEmptyIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  repsEmptyText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 4,
  },
  repsEmptySubtext: {
    fontSize: 11,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  repCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GBC.tan,
    padding: 10,
    marginBottom: 6,
    borderWidth: 2,
    borderColor: GBC.darkTan,
  },
  repHeader: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  repSprite: {
    fontSize: 24,
    marginRight: 10,
  },
  repInfo: {
    flex: 1,
  },
  repName: {
    fontSize: 12,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  repOffice: {
    fontSize: 10,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginTop: 2,
  },
  repAlignment: {
    alignItems: 'flex-end',
    minWidth: 60,
  },
  repAlignValue: {
    fontSize: 18,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  repAlignLabel: {
    fontSize: 8,
    color: GBC.gray,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },

  // Add/Update Address Button
  addAddressButton: {
    backgroundColor: GBC.blue,
    paddingVertical: 10,
    paddingHorizontal: 20,
    marginTop: 12,
    borderWidth: 3,
    borderColor: GBC.darkBlue,
  },
  addAddressButtonText: {
    color: GBC.white,
    fontSize: 14,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
  },
  updateAddressLink: {
    paddingVertical: 8,
    alignItems: 'center',
  },
  updateAddressLinkText: {
    color: GBC.blue,
    fontSize: 10,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
  },

  // Address Modal
  addrModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    padding: 20,
  },
  addrModalContainer: {
    maxHeight: '80%',
  },
  addrModalBox: {
    backgroundColor: GBC.white,
  },
  addrField: {
    marginBottom: 10,
  },
  addrFieldLabel: {
    fontSize: 11,
    fontWeight: 'bold',
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 4,
  },
  addrInput: {
    borderWidth: 2,
    borderColor: GBC.darkTan,
    backgroundColor: GBC.tan,
    padding: 10,
    fontSize: 14,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    color: GBC.black,
  },
  addrSuggestions: {
    borderWidth: 2,
    borderColor: GBC.darkTan,
    backgroundColor: GBC.white,
    marginBottom: 10,
    marginTop: -10,
  },
  addrSuggestionItem: {
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: GBC.tan,
  },
  addrSuggestionText: {
    fontSize: 12,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  addrButtonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    gap: 12,
  },
  addrCancelButton: {
    flex: 1,
    paddingVertical: 12,
    borderWidth: 3,
    borderColor: GBC.darkTan,
    backgroundColor: GBC.tan,
  },
  addrCancelText: {
    color: GBC.gray,
    fontSize: 14,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
  },
  addrSaveButton: {
    flex: 1,
    paddingVertical: 12,
    borderWidth: 3,
    borderColor: GBC.darkBlue,
    backgroundColor: GBC.blue,
  },
  addrSaveText: {
    color: GBC.white,
    fontSize: 14,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
  },
  addrErrorText: {
    color: GBC.red,
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'center',
    marginBottom: 8,
  },

  // Settings Screen
  settingsAddrText: {
    fontSize: 14,
    color: GBC.darkGreen,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    marginBottom: 4,
    textAlign: 'center',
  },
  settingsAddrLink: {
    fontSize: 12,
    color: GBC.blue,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: 'bold',
    textAlign: 'center',
  },
});
