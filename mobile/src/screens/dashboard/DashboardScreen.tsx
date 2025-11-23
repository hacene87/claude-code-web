/**
 * Dashboard Screen
 * ================
 * Implements FR-MOB-002
 */

import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { fetchStatus } from '../../app/store/slices/statusSlice';
import { fetchActiveErrors } from '../../app/store/slices/errorsSlice';
import { RootState, AppDispatch } from '../../app/store';
import StatusCard from '../../components/dashboard/StatusCard';
import MetricsCard from '../../components/dashboard/MetricsCard';
import ActiveErrorsCard from '../../components/dashboard/ActiveErrorsCard';

const DashboardScreen: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigation = useNavigation();
  const { systemStatus, metrics, isLoading, lastUpdated } = useSelector(
    (state: RootState) => state.status
  );
  const { activeErrors } = useSelector((state: RootState) => state.errors);

  const loadData = useCallback(() => {
    dispatch(fetchStatus());
    dispatch(fetchActiveErrors(5));
  }, [dispatch]);

  useEffect(() => {
    loadData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'running':
        return '#27ae60';
      case 'degraded':
        return '#f39c12';
      case 'stopped':
      case 'error':
        return '#e74c3c';
      default:
        return '#95a5a6';
    }
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={isLoading} onRefresh={loadData} />
      }
    >
      {/* System Status Card */}
      {systemStatus && (
        <StatusCard
          status={systemStatus.status}
          statusColor={getStatusColor(systemStatus.status)}
          uptime={formatUptime(systemStatus.uptime_seconds)}
          lastCheck={lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : '-'}
        />
      )}

      {/* Metrics Row */}
      {metrics && (
        <View style={styles.metricsRow}>
          <MetricsCard
            title="Updates"
            value={metrics.updates_today}
            subtitle="today"
            color="#3498db"
          />
          <MetricsCard
            title="Errors"
            value={systemStatus?.active_errors ?? 0}
            subtitle="active"
            color="#e74c3c"
          />
        </View>
      )}

      {/* Fix Success Rate */}
      {metrics && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Fix Success Rate (7 days)</Text>
          <View style={styles.progressContainer}>
            <View
              style={[
                styles.progressBar,
                { width: `${metrics.fix_success_rate_7d}%` },
              ]}
            />
            <Text style={styles.progressText}>
              {metrics.fix_success_rate_7d.toFixed(1)}%
            </Text>
          </View>
        </View>
      )}

      {/* Active Errors */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Active Errors</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Errors' as never)}>
            <Text style={styles.seeAllText}>See All</Text>
          </TouchableOpacity>
        </View>
        {activeErrors.length > 0 ? (
          activeErrors.map((error) => (
            <ActiveErrorsCard
              key={error.id}
              error={error}
              onPress={() => navigation.navigate('ErrorDetail' as never, { errorId: error.id } as never)}
            />
          ))
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateText}>No active errors</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  metricsRow: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  section: {
    padding: 16,
    paddingTop: 0,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  seeAllText: {
    fontSize: 14,
    color: '#3498db',
  },
  progressContainer: {
    backgroundColor: '#ecf0f1',
    borderRadius: 8,
    height: 24,
    overflow: 'hidden',
    position: 'relative',
  },
  progressBar: {
    backgroundColor: '#27ae60',
    height: '100%',
    borderRadius: 8,
  },
  progressText: {
    position: 'absolute',
    right: 8,
    top: 4,
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
  },
  emptyState: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 24,
    alignItems: 'center',
  },
  emptyStateText: {
    color: '#95a5a6',
    fontSize: 14,
  },
});

export default DashboardScreen;
