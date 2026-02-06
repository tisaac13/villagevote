/**
 * Feed Screen
 * The main swipe interface for voting on measures
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Pressable,
  SafeAreaView,
} from 'react-native';
import { SwipeCard } from '@/components/SwipeCard';
import { useFeedStore } from '@/store/feedStore';
import { JurisdictionLevel, VoteValue } from '@/types';

const FILTER_OPTIONS: { label: string; value: JurisdictionLevel | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Federal', value: 'federal' },
  { label: 'State', value: 'state' },
  { label: 'City', value: 'city' },
];

export function FeedScreen() {
  const {
    measures,
    currentIndex,
    isLoading,
    error,
    filter,
    loadFeed,
    vote,
    skipMeasure,
    setFilter,
  } = useFeedStore();

  useEffect(() => {
    loadFeed(true);
  }, []);

  const currentMeasure = measures[currentIndex];

  const handleSwipe = async (voteValue: VoteValue) => {
    if (currentMeasure) {
      try {
        await vote(currentMeasure.id, voteValue);
      } catch (error) {
        console.error('Vote failed:', error);
      }
    }
  };

  const handleSkip = () => {
    skipMeasure();
  };

  const renderContent = () => {
    if (isLoading && measures.length === 0) {
      return (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#3182ce" />
          <Text style={styles.loadingText}>Loading measures...</Text>
        </View>
      );
    }

    if (error) {
      return (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryButton} onPress={() => loadFeed(true)}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </Pressable>
        </View>
      );
    }

    if (!currentMeasure) {
      return (
        <View style={styles.centered}>
          <Text style={styles.emptyTitle}>You're all caught up!</Text>
          <Text style={styles.emptyText}>
            Check back later for more measures to vote on.
          </Text>
          <Pressable style={styles.refreshButton} onPress={() => loadFeed(true)}>
            <Text style={styles.refreshButtonText}>Refresh Feed</Text>
          </Pressable>
        </View>
      );
    }

    return (
      <View style={styles.cardContainer}>
        <SwipeCard
          key={currentMeasure.id}
          measure={currentMeasure}
          onSwipe={handleSwipe}
          onSkip={handleSkip}
        />
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>CivicSwipe</Text>
        <Text style={styles.headerSubtitle}>
          {measures.length - currentIndex} measures remaining
        </Text>
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterContainer}>
        {FILTER_OPTIONS.map((option) => (
          <Pressable
            key={option.value}
            style={[
              styles.filterTab,
              filter === option.value && styles.filterTabActive,
            ]}
            onPress={() => setFilter(option.value)}
          >
            <Text
              style={[
                styles.filterTabText,
                filter === option.value && styles.filterTabTextActive,
              ]}
            >
              {option.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Card Area */}
      {renderContent()}

      {/* Vote Counter */}
      <View style={styles.counter}>
        <Text style={styles.counterText}>
          {currentIndex} of {measures.length} reviewed
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7fafc',
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    backgroundColor: 'white',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1a365d',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#718096',
    marginTop: 4,
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    gap: 8,
  },
  filterTab: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#edf2f7',
  },
  filterTabActive: {
    backgroundColor: '#1a365d',
  },
  filterTabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4a5568',
  },
  filterTabTextActive: {
    color: 'white',
  },
  cardContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  loadingText: {
    fontSize: 16,
    color: '#718096',
    marginTop: 16,
  },
  errorText: {
    fontSize: 16,
    color: '#e53e3e',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#3182ce',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1a365d',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 16,
    color: '#718096',
    textAlign: 'center',
    marginBottom: 24,
  },
  refreshButton: {
    backgroundColor: '#1a365d',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  refreshButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  counter: {
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  counterText: {
    fontSize: 14,
    color: '#718096',
  },
});
