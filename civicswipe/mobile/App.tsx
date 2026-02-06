/**
 * VillageVote Mobile App
 * 32-bit Pokemon GameBoy Color Style
 */
import React, { useEffect, useState, useRef } from 'react';
import { StatusBar } from 'expo-status-bar';
import { View, Text, ActivityIndicator, StyleSheet, TextInput, TouchableOpacity, ScrollView, Platform, Dimensions, Animated, Modal } from 'react-native';

// Simple API base URL
// Use your Mac's IP for iOS simulator, localhost for web
const API_BASE_URL = Platform.OS === 'web'
  ? 'http://localhost:8000/v1'
  : 'http://192.168.1.195:8000/v1';

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
};

// Types
interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  access_token?: string;
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
function HomeScreen({ user, onNavigate }: { user: User; onNavigate: (screen: string) => void }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

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
      {/* Trainer Card */}
      <PixelBox variant="menu" style={styles.trainerCard}>
        <View style={styles.trainerHeader}>
          <Text style={styles.trainerSprite}>👤</Text>
          <View style={styles.trainerInfo}>
            <Text style={styles.trainerName}>{user.first_name.toUpperCase()}</Text>
            <Text style={styles.trainerTitle}>VOTER</Text>
          </View>
        </View>
      </PixelBox>

      {/* Stats Box */}
      {stats && (
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

    </ScrollView>
  );
}

// Vote History Screen - Pokemon Pokedex Style
function HistoryScreen({ user, onNavigate }: { user: User; onNavigate: (screen: string) => void }) {
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
function FeedScreen({ user, onNavigate }: { user: User; onNavigate: (screen: string) => void }) {
  const [measures, setMeasures] = useState<Measure[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [votesCount, setVotesCount] = useState(0);

  useEffect(() => {
    loadMeasures();
  }, []);

  const loadMeasures = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/feed?limit=30&include_skipped=true`, {
        headers: { 'Authorization': `Bearer ${user.access_token}` },
      });
      const data = await response.json();
      const items = (data.items || []).map((item: any) => ({
        id: item.measure_id || item.id,
        title: item.title,
        summary: item.summary_short || item.summary || '',
        level: item.level,
        status: item.status,
        sources: item.sources,
        user_vote: item.user_vote,
        external_id: item.external_id,
      }));
      setMeasures(items);
    } catch (err) {
      console.error('Failed to load measures:', err);
    } finally {
      setIsLoading(false);
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
      setVotesCount(votesCount + 1);
    }
    setCurrentIndex(currentIndex + 1);
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
      {/* Progress Bar - like Pokemon XP bar */}
      <View style={styles.progressBarContainer}>
        <Text style={styles.progressLabel}>PROGRESS</Text>
        <View style={styles.progressBarOuter}>
          <View
            style={[
              styles.progressBarInner,
              { width: `${measures.length > 0 ? (currentIndex / measures.length) * 100 : 0}%` }
            ]}
          />
        </View>
        <Text style={styles.progressText}>{currentIndex}/{measures.length}</Text>
      </View>

      {/* Vote Counter */}
      <View style={styles.voteCounter}>
        <Text style={styles.voteCounterText}>VOTES: {votesCount}</Text>
      </View>

      {currentMeasure ? (
        <SwipeCard measure={currentMeasure} onVote={handleVote} />
      ) : (
        <PixelBox variant="dialog" style={styles.victoryBox}>
          <Text style={styles.victorySprite}>🎉</Text>
          <Text style={styles.victoryTitle}>QUEST COMPLETE!</Text>
          <Text style={styles.victoryText}>You reviewed all available bills!</Text>
          <Text style={styles.victoryStats}>Votes cast: {votesCount}</Text>
          <PixelButton onPress={() => onNavigate('home')} title="RETURN" variant="primary" icon="◄" />
        </PixelBox>
      )}
    </View>
  );
}

// Main App with Navigation - Pokemon Style
function MainApp({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [currentScreen, setCurrentScreen] = useState('home');
  const [menuOpen, setMenuOpen] = useState(false);
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
    setTimeout(() => setCurrentScreen(screen), 100);
  };

  const handleLogout = () => {
    closeMenu();
    setTimeout(() => onLogout(), 100);
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'home':
        return <HomeScreen user={user} onNavigate={setCurrentScreen} />;
      case 'feed':
        return <FeedScreen user={user} onNavigate={setCurrentScreen} />;
      case 'history':
        return <HistoryScreen user={user} onNavigate={setCurrentScreen} />;
      default:
        return <HomeScreen user={user} onNavigate={setCurrentScreen} />;
    }
  };

  return (
    <View style={styles.gbcMainContainer}>
      {/* Top Bar - Pokemon style header */}
      <View style={styles.gbcHeader}>
        <TouchableOpacity onPress={() => setCurrentScreen('home')}>
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
          onPress={() => setCurrentScreen('home')}
        >
          <Text style={styles.gbcTabIcon}>🏠</Text>
          <Text style={[styles.gbcTabLabel, currentScreen === 'home' && styles.gbcTabLabelActive]}>HOME</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.gbcTab, currentScreen === 'feed' && styles.gbcTabActive]}
          onPress={() => setCurrentScreen('feed')}
        >
          <Text style={styles.gbcTabIcon}>🗳️</Text>
          <Text style={[styles.gbcTabLabel, currentScreen === 'feed' && styles.gbcTabLabelActive]}>VOTE</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.gbcTab, currentScreen === 'history' && styles.gbcTabActive]}
          onPress={() => setCurrentScreen('history')}
        >
          <Text style={styles.gbcTabIcon}>📜</Text>
          <Text style={[styles.gbcTabLabel, currentScreen === 'history' && styles.gbcTabLabelActive]}>LOG</Text>
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

            <TouchableOpacity style={styles.slideMenuItem} onPress={() => handleMenuNavigate('home')}>
              <Text style={styles.slideMenuIcon}>🏠</Text>
              <Text style={styles.slideMenuText}>HOME</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.slideMenuItem} onPress={() => handleMenuNavigate('feed')}>
              <Text style={styles.slideMenuIcon}>🗳️</Text>
              <Text style={styles.slideMenuText}>VOTE ON BILLS</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.slideMenuItem} onPress={() => handleMenuNavigate('history')}>
              <Text style={styles.slideMenuIcon}>📜</Text>
              <Text style={styles.slideMenuText}>VOTE HISTORY</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.slideMenuItem, styles.slideMenuItemDisabled]}>
              <Text style={styles.slideMenuIcon}>⚙️</Text>
              <Text style={[styles.slideMenuText, styles.slideMenuTextDisabled]}>SETTINGS</Text>
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

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800);
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
      {user ? <MainApp user={user} onLogout={() => setUser(null)} /> : <LoginScreen onLogin={setUser} />}
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
    backgroundColor: GBC.white,
  },
  gbcScrollView: {
    flex: 1,
    padding: 12,
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
    backgroundColor: GBC.white,
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
    backgroundColor: GBC.white,
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

  // History Screen
  historyGbcContainer: {
    flex: 1,
    backgroundColor: GBC.white,
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
});
