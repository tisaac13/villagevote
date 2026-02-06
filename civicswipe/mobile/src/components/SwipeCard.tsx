/**
 * SwipeCard Component
 * The main card for displaying measures in the swipe feed
 */
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Pressable,
  Linking,
} from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  runOnJS,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { Measure, VoteValue } from '@/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.25;

interface SwipeCardProps {
  measure: Measure;
  onSwipe: (vote: VoteValue) => void;
  onSkip: () => void;
}

export function SwipeCard({ measure, onSwipe, onSkip }: SwipeCardProps) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const handleSwipe = (vote: VoteValue) => {
    onSwipe(vote);
  };

  const gesture = Gesture.Pan()
    .onUpdate((event) => {
      translateX.value = event.translationX;
      translateY.value = event.translationY * 0.5;
    })
    .onEnd((event) => {
      if (event.translationX > SWIPE_THRESHOLD) {
        // Swiped right - YES
        translateX.value = withSpring(SCREEN_WIDTH * 1.5);
        runOnJS(handleSwipe)('yes');
      } else if (event.translationX < -SWIPE_THRESHOLD) {
        // Swiped left - NO
        translateX.value = withSpring(-SCREEN_WIDTH * 1.5);
        runOnJS(handleSwipe)('no');
      } else {
        // Return to center
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
      }
    });

  const cardStyle = useAnimatedStyle(() => {
    const rotate = interpolate(
      translateX.value,
      [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
      [-15, 0, 15],
      Extrapolation.CLAMP
    );

    return {
      transform: [
        { translateX: translateX.value },
        { translateY: translateY.value },
        { rotate: `${rotate}deg` },
      ],
    };
  });

  const yesOverlayStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      translateX.value,
      [0, SWIPE_THRESHOLD],
      [0, 1],
      Extrapolation.CLAMP
    );
    return { opacity };
  });

  const noOverlayStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      translateX.value,
      [-SWIPE_THRESHOLD, 0],
      [1, 0],
      Extrapolation.CLAMP
    );
    return { opacity };
  });

  const getLevelColor = () => {
    switch (measure.level) {
      case 'federal':
        return '#1a365d';
      case 'state':
        return '#2d3748';
      case 'county':
        return '#4a5568';
      case 'city':
        return '#718096';
      default:
        return '#2d3748';
    }
  };

  const getLevelLabel = () => {
    switch (measure.level) {
      case 'federal':
        return 'U.S. Congress';
      case 'state':
        return 'Arizona Legislature';
      case 'city':
        return 'City of Phoenix';
      default:
        return measure.level.toUpperCase();
    }
  };

  const getStatusColor = () => {
    switch (measure.status) {
      case 'passed':
        return '#38a169';
      case 'failed':
        return '#e53e3e';
      case 'scheduled':
        return '#3182ce';
      case 'in_committee':
        return '#d69e2e';
      default:
        return '#718096';
    }
  };

  const openSource = () => {
    const primarySource = measure.sources?.find((s) => s.is_primary);
    if (primarySource?.url) {
      Linking.openURL(primarySource.url);
    }
  };

  return (
    <GestureDetector gesture={gesture}>
      <Animated.View style={[styles.card, cardStyle]}>
        <LinearGradient
          colors={[getLevelColor(), '#1a202c']}
          style={styles.gradient}
        >
          {/* YES Overlay */}
          <Animated.View style={[styles.overlay, styles.yesOverlay, yesOverlayStyle]}>
            <Text style={styles.overlayText}>YES</Text>
          </Animated.View>

          {/* NO Overlay */}
          <Animated.View style={[styles.overlay, styles.noOverlay, noOverlayStyle]}>
            <Text style={styles.overlayText}>NO</Text>
          </Animated.View>

          {/* Card Content */}
          <View style={styles.content}>
            {/* Header */}
            <View style={styles.header}>
              <View style={styles.levelBadge}>
                <Text style={styles.levelText}>{getLevelLabel()}</Text>
              </View>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor() }]}>
                <Text style={styles.statusText}>{measure.status.replace('_', ' ')}</Text>
              </View>
            </View>

            {/* Title */}
            <Text style={styles.title} numberOfLines={4}>
              {measure.title}
            </Text>

            {/* Summary */}
            {measure.summary_short && (
              <Text style={styles.summary} numberOfLines={6}>
                {measure.summary_short}
              </Text>
            )}

            {/* Topics */}
            {measure.topic_tags && measure.topic_tags.length > 0 && (
              <View style={styles.topics}>
                {measure.topic_tags.slice(0, 3).map((topic, index) => (
                  <View key={index} style={styles.topicBadge}>
                    <Text style={styles.topicText}>{topic}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Footer */}
            <View style={styles.footer}>
              <Pressable onPress={openSource} style={styles.sourceButton}>
                <Text style={styles.sourceText}>View Full Details →</Text>
              </Pressable>
            </View>
          </View>

          {/* Swipe Instructions */}
          <View style={styles.instructions}>
            <Text style={styles.instructionText}>← NO</Text>
            <Pressable onPress={onSkip}>
              <Text style={styles.skipText}>SKIP</Text>
            </Pressable>
            <Text style={styles.instructionText}>YES →</Text>
          </View>
        </LinearGradient>
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  card: {
    width: SCREEN_WIDTH - 32,
    height: '85%',
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  gradient: {
    flex: 1,
    padding: 20,
  },
  overlay: {
    position: 'absolute',
    top: 40,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 4,
    zIndex: 10,
  },
  yesOverlay: {
    right: 20,
    borderColor: '#38a169',
    backgroundColor: 'rgba(56, 161, 105, 0.2)',
    transform: [{ rotate: '15deg' }],
  },
  noOverlay: {
    left: 20,
    borderColor: '#e53e3e',
    backgroundColor: 'rgba(229, 62, 62, 0.2)',
    transform: [{ rotate: '-15deg' }],
  },
  overlayText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: 'white',
  },
  content: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  levelBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  levelText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 16,
    lineHeight: 28,
  },
  summary: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: 24,
    marginBottom: 16,
  },
  topics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  topicBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  topicText: {
    color: 'rgba(255, 255, 255, 0.9)',
    fontSize: 12,
  },
  footer: {
    marginTop: 'auto',
  },
  sourceButton: {
    alignSelf: 'flex-start',
  },
  sourceText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  instructions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  instructionText: {
    color: 'rgba(255, 255, 255, 0.5)',
    fontSize: 14,
    fontWeight: '600',
  },
  skipText: {
    color: 'rgba(255, 255, 255, 0.5)',
    fontSize: 14,
    fontWeight: '600',
    padding: 10,
  },
});
