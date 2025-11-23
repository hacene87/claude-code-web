/**
 * Active Errors Card Component
 * ============================
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ErrorSummary } from '../../types/api.types';

interface ActiveErrorsCardProps {
  error: ErrorSummary;
  onPress: () => void;
}

const ActiveErrorsCard: React.FC<ActiveErrorsCardProps> = ({ error, onPress }) => {
  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'fixing':
        return '..';
      case 'queued':
        return '...';
      default:
        return '!';
    }
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'fixing':
        return `Fixing... (${error.attempts}/5)`;
      case 'queued':
        return 'Queued';
      case 'detected':
        return 'Detected';
      default:
        return status;
    }
  };

  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>{getStatusIcon(error.status)}</Text>
      </View>
      <View style={styles.content}>
        <Text style={styles.errorType}>{error.error_type}</Text>
        <View style={styles.row}>
          <Text style={styles.moduleName}>
            {error.module_name || 'Unknown'}
          </Text>
          <Text style={styles.separator}>|</Text>
          <Text style={styles.status}>{getStatusText(error.status)}</Text>
        </View>
      </View>
      <Text style={styles.arrow}>{'>'}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#f39c12',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  icon: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  content: {
    flex: 1,
  },
  errorType: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 2,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  moduleName: {
    fontSize: 12,
    color: '#3498db',
  },
  separator: {
    marginHorizontal: 6,
    color: '#bdc3c7',
  },
  status: {
    fontSize: 12,
    color: '#7f8c8d',
  },
  arrow: {
    fontSize: 16,
    color: '#bdc3c7',
    marginLeft: 8,
  },
});

export default ActiveErrorsCard;
