import { apiClient } from './client';
import { LatencyHeatmapResponse, PerformanceComparisonResponse, ExecutionRejectionResponse } from './types';

export const analyticsApi = {
  getLatencyHeatmap: async (): Promise<LatencyHeatmapResponse> => {
    const response = await apiClient.get<LatencyHeatmapResponse>('/api/v1/analytics/latency/heatmap');
    return response.data;
  },

  getPerformanceComparison: async (): Promise<PerformanceComparisonResponse> => {
    const response = await apiClient.get<PerformanceComparisonResponse>('/api/v1/analytics/performance/comparison');
    return response.data;
  },

  getExecutionRejections: async (): Promise<ExecutionRejectionResponse> => {
    const response = await apiClient.get<ExecutionRejectionResponse>('/api/v1/analytics/execution/rejections');
    return response.data;
  },
};
