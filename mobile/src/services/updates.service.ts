/**
 * Updates Service
 * ===============
 */

import api from './api';
import {
  UpdateList,
  UpdateDetail,
  TriggerUpdateRequest,
  TriggerUpdateResponse,
} from '../types/api.types';

export interface UpdateListParams {
  status?: string;
  module?: string;
  limit?: number;
  offset?: number;
}

export const updatesService = {
  async getUpdates(params?: UpdateListParams): Promise<UpdateList> {
    return api.get<UpdateList>('/api/v1/updates', params);
  },

  async getUpdate(id: number): Promise<UpdateDetail> {
    return api.get<UpdateDetail>(`/api/v1/updates/${id}`);
  },

  async triggerUpdate(request: TriggerUpdateRequest): Promise<TriggerUpdateResponse> {
    return api.post<TriggerUpdateResponse>('/api/v1/updates/trigger', request);
  },

  async retryUpdate(id: number): Promise<TriggerUpdateResponse> {
    return api.post<TriggerUpdateResponse>(`/api/v1/updates/${id}/retry`);
  },
};

export default updatesService;
