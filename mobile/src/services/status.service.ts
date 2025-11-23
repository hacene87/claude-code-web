/**
 * Status Service
 * ==============
 */

import api from './api';
import { SystemStatus, ComponentStatus, Metrics } from '../types/api.types';

export const statusService = {
  async getSystemStatus(): Promise<SystemStatus> {
    return api.get<SystemStatus>('/api/v1/status');
  },

  async getComponentStatus(): Promise<ComponentStatus[]> {
    return api.get<ComponentStatus[]>('/api/v1/status/components');
  },

  async getMetrics(): Promise<Metrics> {
    return api.get<Metrics>('/api/v1/status/metrics');
  },
};

export default statusService;
