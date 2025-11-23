/**
 * Redux Store Configuration
 * =========================
 */

import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import statusReducer from './slices/statusSlice';
import updatesReducer from './slices/updatesSlice';
import errorsReducer from './slices/errorsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    status: statusReducer,
    updates: updatesReducer,
    errors: errorsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;
