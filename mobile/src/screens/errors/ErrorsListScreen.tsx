/**
 * Errors List Screen
 * ==================
 * Implements FR-MOB-003 (similar to updates)
 */

import React, { useEffect, useCallback, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { fetchErrors, resetErrors } from '../../app/store/slices/errorsSlice';
import { RootState, AppDispatch } from '../../app/store';
import { ErrorSummary, ErrorSeverity } from '../../types/api.types';

const PAGE_SIZE = 20;

const ErrorsListScreen: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigation = useNavigation();
  const { items, total, isLoading, hasMore } = useSelector(
    (state: RootState) => state.errors
  );

  const [filter, setFilter] = useState<string | undefined>();

  const loadErrors = useCallback(
    (refresh = false) => {
      if (refresh) {
        dispatch(resetErrors());
      }
      dispatch(
        fetchErrors({
          status: filter,
          limit: PAGE_SIZE,
          offset: refresh ? 0 : items.length,
        })
      );
    },
    [dispatch, filter, items.length]
  );

  useEffect(() => {
    loadErrors(true);
  }, [filter]);

  const loadMore = () => {
    if (!isLoading && hasMore) {
      loadErrors(false);
    }
  };

  const getSeverityColor = (severity: ErrorSeverity): string => {
    switch (severity) {
      case 'CRITICAL':
        return '#c0392b';
      case 'HIGH':
        return '#e74c3c';
      case 'MEDIUM':
        return '#f39c12';
      case 'LOW':
        return '#27ae60';
      default:
        return '#95a5a6';
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      detected: '#3498db',
      queued: '#9b59b6',
      fixing: '#f39c12',
      resolved: '#27ae60',
      failed: '#e74c3c',
      ignored: '#95a5a6',
    };
    return colors[status] || '#95a5a6';
  };

  const renderError = ({ item }: { item: ErrorSummary }) => (
    <TouchableOpacity
      style={styles.errorCard}
      onPress={() => navigation.navigate('ErrorDetail' as never, { errorId: item.id } as never)}
    >
      <View style={styles.cardHeader}>
        <View style={[styles.severityBadge, { backgroundColor: getSeverityColor(item.severity) }]}>
          <Text style={styles.severityText}>{item.severity}</Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getStatusBadge(item.status) }]}>
          <Text style={styles.statusText}>{item.status}</Text>
        </View>
      </View>

      <Text style={styles.errorType}>{item.error_type}</Text>
      <Text style={styles.errorMessage} numberOfLines={2}>
        {item.message}
      </Text>

      <View style={styles.cardFooter}>
        {item.module_name && (
          <Text style={styles.moduleName}>{item.module_name}</Text>
        )}
        <Text style={styles.timestamp}>
          {new Date(item.detected_at).toLocaleString()}
        </Text>
      </View>

      {item.attempts > 0 && (
        <Text style={styles.attempts}>Attempts: {item.attempts}/5</Text>
      )}
    </TouchableOpacity>
  );

  const renderFooter = () => {
    if (!isLoading) return null;
    return (
      <View style={styles.footer}>
        <ActivityIndicator size="small" color="#3498db" />
      </View>
    );
  };

  const FilterButton: React.FC<{ label: string; value: string | undefined }> = ({
    label,
    value,
  }) => (
    <TouchableOpacity
      style={[styles.filterButton, filter === value && styles.filterButtonActive]}
      onPress={() => setFilter(value)}
    >
      <Text
        style={[
          styles.filterButtonText,
          filter === value && styles.filterButtonTextActive,
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      {/* Filters */}
      <View style={styles.filterContainer}>
        <FilterButton label="All" value={undefined} />
        <FilterButton label="Active" value="fixing" />
        <FilterButton label="Failed" value="failed" />
        <FilterButton label="Resolved" value="resolved" />
      </View>

      {/* Error List */}
      <FlatList
        data={items}
        renderItem={renderError}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isLoading && items.length === 0}
            onRefresh={() => loadErrors(true)}
          />
        }
        onEndReached={loadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={renderFooter}
        ListEmptyComponent={
          !isLoading ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>No errors found</Text>
            </View>
          ) : null
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
    gap: 8,
  },
  filterButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#ecf0f1',
  },
  filterButtonActive: {
    backgroundColor: '#3498db',
  },
  filterButtonText: {
    fontSize: 12,
    color: '#7f8c8d',
  },
  filterButtonTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 12,
  },
  errorCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  severityText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusText: {
    color: '#fff',
    fontSize: 10,
  },
  errorType: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  errorMessage: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  moduleName: {
    fontSize: 12,
    color: '#3498db',
  },
  timestamp: {
    fontSize: 12,
    color: '#95a5a6',
  },
  attempts: {
    fontSize: 11,
    color: '#f39c12',
    marginTop: 4,
  },
  footer: {
    padding: 16,
    alignItems: 'center',
  },
  emptyState: {
    padding: 32,
    alignItems: 'center',
  },
  emptyStateText: {
    color: '#95a5a6',
    fontSize: 14,
  },
});

export default ErrorsListScreen;
