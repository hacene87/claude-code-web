/**
 * Errors Service
 * ==============
 */

import api from './api';
import { ErrorList, ErrorDetail, ErrorSummary } from '../types/api.types';

export interface ErrorListParams {
  status?: string;
  severity?: string;
  category?: string;
  module?: string;
  limit?: number;
  offset?: number;
}

export const errorsService = {
  async getErrors(params?: ErrorListParams): Promise<ErrorList> {
    return api.get<ErrorList>('/api/v1/errors', params);
  },

  async getActiveErrors(limit?: number): Promise<ErrorSummary[]> {
    return api.get<ErrorSummary[]>('/api/v1/errors/active', { limit });
  },

  async getError(id: string): Promise<ErrorDetail> {
    return api.get<ErrorDetail>(`/api/v1/errors/${id}`);
  },

  async retryError(id: string): Promise<{ status: string; attempt_number: number }> {
    return api.post(`/api/v1/errors/${id}/retry`);
  },

  async ignoreError(id: string): Promise<{ status: string }> {
    return api.post(`/api/v1/errors/${id}/ignore`);
  },
};

export default errorsService;
