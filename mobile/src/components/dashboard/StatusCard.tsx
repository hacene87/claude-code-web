/**
 * Status Card Component
 * =====================
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface StatusCardProps {
  status: string;
  statusColor: string;
  uptime: string;
  lastCheck: string;
}

const StatusCard: React.FC<StatusCardProps> = ({
  status,
  statusColor,
  uptime,
  lastCheck,
}) => {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>SYSTEM STATUS</Text>
      <View style={styles.statusRow}>
        <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
        <Text style={styles.statusText}>{status.charAt(0).toUpperCase() + status.slice(1)}</Text>
      </View>
      <View style={styles.detailsRow}>
        <Text style={styles.detailLabel}>Uptime:</Text>
        <Text style={styles.detailValue}>{uptime}</Text>
      </View>
      <View style={styles.detailsRow}>
        <Text style={styles.detailLabel}>Last Check:</Text>
        <Text style={styles.detailValue}>{lastCheck}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    margin: 16,
    marginBottom: 0,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 12,
    fontWeight: '600',
    color: '#95a5a6',
    marginBottom: 12,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 8,
  },
  statusText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  detailsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  detailLabel: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  detailValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
});

export default StatusCard;
