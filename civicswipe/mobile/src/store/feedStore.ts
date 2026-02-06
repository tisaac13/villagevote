/**
 * Feed Store
 * Manages the swipe feed state and voting
 */
import { create } from 'zustand';
import { api } from '@/services/api';
import { Measure, UserVote, VoteValue, JurisdictionLevel } from '@/types';

interface FeedState {
  // State
  measures: Measure[];
  currentIndex: number;
  isLoading: boolean;
  error: string | null;
  filter: JurisdictionLevel | 'all';

  // Voting state
  myVotes: UserVote[];
  votesLoading: boolean;

  // Actions
  loadFeed: (refresh?: boolean) => Promise<void>;
  vote: (measureId: string, vote: VoteValue) => Promise<void>;
  skipMeasure: () => void;
  setFilter: (filter: JurisdictionLevel | 'all') => void;
  loadMyVotes: () => Promise<void>;
  undoVote: (measureId: string) => Promise<void>;
}

export const useFeedStore = create<FeedState>((set, get) => ({
  // Initial state
  measures: [],
  currentIndex: 0,
  isLoading: false,
  error: null,
  filter: 'all',
  myVotes: [],
  votesLoading: false,

  // Load feed measures
  loadFeed: async (refresh = false) => {
    try {
      set({ isLoading: true, error: null });

      const { filter } = get();
      const params: any = { limit: 20 };

      if (filter !== 'all') {
        params.level = filter;
      }

      const measures = await api.getFeed(params);

      if (refresh) {
        set({ measures, currentIndex: 0, isLoading: false });
      } else {
        set((state) => ({
          measures: [...state.measures, ...measures],
          isLoading: false,
        }));
      }
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to load feed';
      set({ error: message, isLoading: false });
    }
  },

  // Vote on a measure
  vote: async (measureId: string, vote: VoteValue) => {
    try {
      const userVote = await api.vote(measureId, vote);

      // Add to my votes
      set((state) => ({
        myVotes: [userVote, ...state.myVotes],
        currentIndex: state.currentIndex + 1,
      }));

      // Load more measures if running low
      const { measures, currentIndex } = get();
      if (currentIndex >= measures.length - 5) {
        get().loadFeed();
      }
    } catch (error: any) {
      console.error('Vote failed:', error);
      throw error;
    }
  },

  // Skip current measure without voting
  skipMeasure: () => {
    set((state) => ({
      currentIndex: state.currentIndex + 1,
    }));

    // Load more measures if running low
    const { measures, currentIndex } = get();
    if (currentIndex >= measures.length - 5) {
      get().loadFeed();
    }
  },

  // Set filter level
  setFilter: (filter: JurisdictionLevel | 'all') => {
    set({ filter });
    get().loadFeed(true);
  },

  // Load user's vote history
  loadMyVotes: async () => {
    try {
      set({ votesLoading: true });
      const votes = await api.getMyVotes({ limit: 50 });
      set({ myVotes: votes, votesLoading: false });
    } catch (error) {
      console.error('Failed to load votes:', error);
      set({ votesLoading: false });
    }
  },

  // Undo a vote
  undoVote: async (measureId: string) => {
    try {
      await api.deleteVote(measureId);
      set((state) => ({
        myVotes: state.myVotes.filter((v) => v.measure_id !== measureId),
      }));
    } catch (error) {
      console.error('Failed to undo vote:', error);
      throw error;
    }
  },
}));
