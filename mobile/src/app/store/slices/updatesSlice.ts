/**
 * Updates Slice
 * =============
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { UpdateSummary } from '../../../types/api.types';
import updatesService, { UpdateListParams } from '../../../services/updates.service';

interface UpdatesState {
  items: UpdateSummary[];
  total: number;
  isLoading: boolean;
  error: string | null;
  currentPage: number;
  hasMore: boolean;
}

const initialState: UpdatesState = {
  items: [],
  total: 0,
  isLoading: false,
  error: null,
  currentPage: 0,
  hasMore: true,
};

export const fetchUpdates = createAsyncThunk(
  'updates/fetch',
  async (params: UpdateListParams = {}, { rejectWithValue }) => {
    try {
      const result = await updatesService.getUpdates(params);
      return { ...result, append: (params.offset ?? 0) > 0 };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch updates');
    }
  }
);

export const triggerUpdate = createAsyncThunk(
  'updates/trigger',
  async (modules: string[], { rejectWithValue }) => {
    try {
      return await updatesService.triggerUpdate({ modules });
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to trigger update');
    }
  }
);

const updatesSlice = createSlice({
  name: 'updates',
  initialState,
  reducers: {
    addUpdate: (state, action: PayloadAction<UpdateSummary>) => {
      state.items.unshift(action.payload);
      state.total += 1;
    },
    updateItem: (state, action: PayloadAction<UpdateSummary>) => {
      const index = state.items.findIndex((item) => item.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = action.payload;
      }
    },
    resetUpdates: (state) => {
      state.items = [];
      state.total = 0;
      state.currentPage = 0;
      state.hasMore = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUpdates.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchUpdates.fulfilled, (state, action) => {
        state.isLoading = false;
        if (action.payload.append) {
          state.items = [...state.items, ...action.payload.items];
        } else {
          state.items = action.payload.items;
        }
        state.total = action.payload.total;
        state.hasMore = state.items.length < action.payload.total;
        state.currentPage += 1;
      })
      .addCase(fetchUpdates.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { addUpdate, updateItem, resetUpdates } = updatesSlice.actions;
export default updatesSlice.reducer;
