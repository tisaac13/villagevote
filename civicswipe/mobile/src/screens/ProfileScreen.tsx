/**
 * Profile Screen
 */
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { useAuthStore } from '@/store/authStore';

export function ProfileScreen() {
  const { user, profile, logout } = useAuthStore();

  const handleLogout = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: logout,
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </Text>
          </View>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        {/* Location Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Your Location</Text>
          <View style={styles.locationInfo}>
            <Text style={styles.locationText}>
              {profile?.address?.city}, {profile?.address?.state} {profile?.address?.postal_code}
            </Text>
          </View>
          <Text style={styles.cardSubtext}>
            Your address is encrypted and only used to show relevant legislation
          </Text>
        </View>

        {/* Preferences Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Preferences</Text>

          <View style={styles.preferenceItem}>
            <Text style={styles.preferenceLabel}>Notifications</Text>
            <Text style={styles.preferenceValue}>
              {profile?.preferences?.notify_enabled ? 'Enabled' : 'Disabled'}
            </Text>
          </View>

          <View style={styles.preferenceItem}>
            <Text style={styles.preferenceLabel}>Topics</Text>
            <Text style={styles.preferenceValue}>
              {profile?.preferences?.topics?.length || 0} selected
            </Text>
          </View>
        </View>

        {/* Stats Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Your Activity</Text>

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>0</Text>
              <Text style={styles.statLabel}>Total Votes</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>0</Text>
              <Text style={styles.statLabel}>Matches</Text>
            </View>
          </View>
        </View>

        {/* About Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>About RepCheck</Text>
          <Text style={styles.aboutText}>
            RepCheck helps you stay informed about legislation at all levels
            of government. Swipe right to support, left to oppose, and see how
            your positions align with your elected representatives.
          </Text>
          <Text style={styles.version}>Version 1.0.0</Text>
        </View>

        {/* Sign Out Button */}
        <Pressable style={styles.signOutButton} onPress={handleLogout}>
          <Text style={styles.signOutText}>Sign Out</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7fafc',
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#1a365d',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: 'white',
  },
  email: {
    fontSize: 18,
    color: '#2d3748',
    fontWeight: '500',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1a365d',
    marginBottom: 12,
  },
  cardSubtext: {
    fontSize: 12,
    color: '#718096',
    marginTop: 8,
  },
  locationInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  locationText: {
    fontSize: 16,
    color: '#2d3748',
  },
  preferenceItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  preferenceLabel: {
    fontSize: 16,
    color: '#4a5568',
  },
  preferenceValue: {
    fontSize: 16,
    color: '#718096',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 16,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#f7fafc',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1a365d',
  },
  statLabel: {
    fontSize: 12,
    color: '#718096',
    marginTop: 4,
  },
  aboutText: {
    fontSize: 14,
    color: '#4a5568',
    lineHeight: 22,
  },
  version: {
    fontSize: 12,
    color: '#a0aec0',
    marginTop: 12,
  },
  signOutButton: {
    backgroundColor: '#e53e3e',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 24,
  },
  signOutText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
