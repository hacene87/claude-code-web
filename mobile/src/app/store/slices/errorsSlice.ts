/**
 * Errors Slice
 * ============
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ErrorSummary } from '../../../types/api.types';
import errorsService, { ErrorListParams } from '../../../services/errors.service';

interface ErrorsState {
  items: ErrorSummary[];
  activeErrors: ErrorSummary[];
  total: number;
  isLoading: boolean;
  error: string | null;
  currentPage: number;
  hasMore: boolean;
}

const initialState: ErrorsState = {
  items: [],
  activeErrors: [],
  total: 0,
  isLoading: false,
  error: null,
  currentPage: 0,
  hasMore: true,
};

export const fetchErrors = createAsyncThunk(
  'errors/fetch',
  async (params: ErrorListParams = {}, { rejectWithValue }) => {
    try {
      const result = await errorsService.getErrors(params);
      return { ...result, append: (params.offset ?? 0) > 0 };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch errors');
    }
  }
);

export const fetchActiveErrors = createAsyncThunk(
  'errors/fetchActive',
  async (limit: number = 10, { rejectWithValue }) => {
    try {
      return await errorsService.getActiveErrors(limit);
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch active errors');
    }
  }
);

export const retryError = createAsyncThunk(
  'errors/retry',
  async (errorId: string, { rejectWithValue }) => {
    try {
      return await errorsService.retryError(errorId);
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to retry error');
    }
  }
);

export const ignoreError = createAsyncThunk(
  'errors/ignore',
  async (errorId: string, { rejectWithValue }) => {
    try {
      await errorsService.ignoreError(errorId);
      return errorId;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to ignore error');
    }
  }
);

const errorsSlice = createSlice({
  name: 'errors',
  initialState,
  reducers: {
    addError: (state, action: PayloadAction<ErrorSummary>) => {
      state.items.unshift(action.payload);
      state.activeErrors.unshift(action.payload);
      state.total += 1;
    },
    updateError: (state, action: PayloadAction<ErrorSummary>) => {
      const index = state.items.findIndex((item) => item.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = action.payload;
      }
      const activeIndex = state.activeErrors.findIndex((item) => item.id === action.payload.id);
      if (activeIndex !== -1) {
        if (['resolved', 'failed', 'ignored'].includes(action.payload.status)) {
          state.activeErrors.splice(activeIndex, 1);
        } else {
          state.activeErrors[activeIndex] = action.payload;
        }
      }
    },
    resetErrors: (state) => {
      state.items = [];
      state.total = 0;
      state.currentPage = 0;
      state.hasMore = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchErrors.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchErrors.fulfilled, (state, action) => {
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
      .addCase(fetchErrors.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchActiveErrors.fulfilled, (state, action) => {
        state.activeErrors = action.payload;
      })
      .addCase(ignoreError.fulfilled, (state, action) => {
        const errorId = action.payload;
        const index = state.items.findIndex((item) => item.id === errorId);
        if (index !== -1) {
          state.items[index].status = 'ignored';
        }
        state.activeErrors = state.activeErrors.filter((item) => item.id !== errorId);
      });
  },
});

export const { addError, updateError, resetErrors } = errorsSlice.actions;
export default errorsSlice.reducer;
