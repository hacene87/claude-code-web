/**
 * Status Slice
 * ============
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { SystemStatus, Metrics } from '../../../types/api.types';
import statusService from '../../../services/status.service';

interface StatusState {
  systemStatus: SystemStatus | null;
  metrics: Metrics | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

const initialState: StatusState = {
  systemStatus: null,
  metrics: null,
  isLoading: false,
  error: null,
  lastUpdated: null,
};

export const fetchStatus = createAsyncThunk('status/fetch', async (_, { rejectWithValue }) => {
  try {
    const [systemStatus, metrics] = await Promise.all([
      statusService.getSystemStatus(),
      statusService.getMetrics(),
    ]);
    return { systemStatus, metrics };
  } catch (error: any) {
    return rejectWithValue(error.message || 'Failed to fetch status');
  }
});

const statusSlice = createSlice({
  name: 'status',
  initialState,
  reducers: {
    updateStatus: (state, action: PayloadAction<Partial<SystemStatus>>) => {
      if (state.systemStatus) {
        state.systemStatus = { ...state.systemStatus, ...action.payload };
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchStatus.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchStatus.fulfilled, (state, action) => {
        state.isLoading = false;
        state.systemStatus = action.payload.systemStatus;
        state.metrics = action.payload.metrics;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchStatus.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { updateStatus } = statusSlice.actions;
export default statusSlice.reducer;
