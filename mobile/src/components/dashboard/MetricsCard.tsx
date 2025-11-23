/**
 * Metrics Card Component
 * ======================
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface MetricsCardProps {
  title: string;
  value: number;
  subtitle: string;
  color: string;
}

const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  subtitle,
  color,
}) => {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={[styles.value, { color }]}>{value}</Text>
      <Text style={styles.subtitle}>{subtitle}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 12,
    color: '#95a5a6',
    marginBottom: 8,
  },
  value: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: 12,
    color: '#7f8c8d',
    marginTop: 4,
  },
});

export default MetricsCard;
