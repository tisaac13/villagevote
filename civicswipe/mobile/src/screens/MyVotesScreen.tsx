/**
 * My Votes Screen
 * Shows the user's voting history
 */
import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { useFeedStore } from '@/store/feedStore';
import { UserVote } from '@/types';

export function MyVotesScreen() {
  const { myVotes, votesLoading, loadMyVotes, undoVote } = useFeedStore();

  useEffect(() => {
    loadMyVotes();
  }, []);

  const handleUndo = async (measureId: string) => {
    try {
      await undoVote(measureId);
    } catch (error) {
      console.error('Failed to undo vote:', error);
    }
  };

  const renderVoteItem = ({ item }: { item: UserVote }) => {
    const isYes = item.vote === 'yes';

    return (
      <View style={styles.voteItem}>
        <View style={styles.voteHeader}>
          <View
            style={[
              styles.voteBadge,
              isYes ? styles.yesBadge : styles.noBadge,
            ]}
          >
            <Text style={styles.voteBadgeText}>
              {isYes ? 'YES' : 'NO'}
            </Text>
          </View>
          <Text style={styles.voteDate}>
            {new Date(item.voted_at).toLocaleDateString()}
          </Text>
        </View>

        <Text style={styles.voteTitle} numberOfLines={3}>
          {item.measure?.title || 'Measure details unavailable'}
        </Text>

        {item.measure?.summary_short && (
          <Text style={styles.voteSummary} numberOfLines={2}>
            {item.measure.summary_short}
          </Text>
        )}

        <View style={styles.voteFooter}>
          {item.measure?.level && (
            <View style={styles.levelBadge}>
              <Text style={styles.levelText}>
                {item.measure.level.toUpperCase()}
              </Text>
            </View>
          )}
          <Pressable
            style={styles.undoButton}
            onPress={() => handleUndo(item.measure_id)}
          >
            <Text style={styles.undoText}>Undo</Text>
          </Pressable>
        </View>
      </View>
    );
  };

  if (votesLoading && myVotes.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#3182ce" />
          <Text style={styles.loadingText}>Loading your votes...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Votes</Text>
        <Text style={styles.headerSubtitle}>
          {myVotes.length} votes recorded
        </Text>
      </View>

      {/* Stats */}
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <Text style={styles.statNumber}>
            {myVotes.filter((v) => v.vote === 'yes').length}
          </Text>
          <Text style={styles.statLabel}>Yes Votes</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={styles.statNumber}>
            {myVotes.filter((v) => v.vote === 'no').length}
          </Text>
          <Text style={styles.statLabel}>No Votes</Text>
        </View>
      </View>

      {/* Vote List */}
      {myVotes.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No votes yet</Text>
          <Text style={styles.emptyText}>
            Start swiping on measures to build your voting record
          </Text>
        </View>
      ) : (
        <FlatList
          data={myVotes}
          renderItem={renderVoteItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7fafc',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#718096',
    marginTop: 16,
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
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    paddingVertical: 20,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#1a365d',
  },
  statLabel: {
    fontSize: 14,
    color: '#718096',
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    backgroundColor: '#e2e8f0',
  },
  listContent: {
    padding: 16,
    gap: 12,
  },
  voteItem: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  voteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  voteBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  yesBadge: {
    backgroundColor: '#c6f6d5',
  },
  noBadge: {
    backgroundColor: '#fed7d7',
  },
  voteBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  voteDate: {
    fontSize: 12,
    color: '#718096',
  },
  voteTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2d3748',
    lineHeight: 22,
    marginBottom: 8,
  },
  voteSummary: {
    fontSize: 14,
    color: '#718096',
    lineHeight: 20,
    marginBottom: 12,
  },
  voteFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  levelBadge: {
    backgroundColor: '#edf2f7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  levelText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#4a5568',
  },
  undoButton: {
    padding: 8,
  },
  undoText: {
    fontSize: 14,
    color: '#e53e3e',
    fontWeight: '600',
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2d3748',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 16,
    color: '#718096',
    textAlign: 'center',
  },
});
