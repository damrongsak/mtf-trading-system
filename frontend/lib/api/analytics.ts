import { apiClient } from './client';
import { 
  LatencyHeatmapResponse, 
  PerformanceComparisonResponse, 
  ExecutionRejectionResponse,
  AccountHistoryResponse,
  HRPWeightsResponse,
  DriftAlertsResponse,
  APIResponse,
  QueueHealth,
  PipelineStatus,
  FundRiskConfig,
  RiskAdjustmentRequest,
  KillSwitchRequest,
  RiskRecommendation,
  RebalanceHistoryItem
} from './types';

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

  getAccountHistory: async (accountId: string, limit: number = 100): Promise<AccountHistoryResponse> => {
    const response = await apiClient.get<AccountHistoryResponse>(`/api/v1/analytics/accounts/${accountId}/history`, {
      params: { limit }
    });
    return response.data;
  },

  getHRPWeights: async (fundId: string): Promise<HRPWeightsResponse> => {
    const response = await apiClient.get<HRPWeightsResponse>(`/api/v1/analytics/funds/${fundId}/hrp-weights`);
    return response.data;
  },

  getDriftAlerts: async (): Promise<DriftAlertsResponse> => {
    const response = await apiClient.get<DriftAlertsResponse>('/api/v1/analytics/alerts/drift');
    return response.data;
  },

  getQueueHealth: async (): Promise<APIResponse<QueueHealth>> => {
    const response = await apiClient.get<APIResponse<QueueHealth>>('/api/v1/system/queue-health');
    return response.data;
  },

  getPipelineStatus: async (): Promise<APIResponse<PipelineStatus>> => {
    const response = await apiClient.get<APIResponse<PipelineStatus>>('/api/v1/orchestration/pipeline/status');
    return response.data;
  },

  getFundRiskConfig: async (fundId: string): Promise<APIResponse<FundRiskConfig>> => {
    const response = await apiClient.get<APIResponse<FundRiskConfig>>(`/api/v1/risk/fund/${fundId}/config`);
    return response.data;
  },

  updateFundRiskConfig: async (fundId: string, req: RiskAdjustmentRequest): Promise<APIResponse<FundRiskConfig>> => {
    const response = await apiClient.patch<APIResponse<FundRiskConfig>>(`/api/v1/risk/fund/${fundId}/config`, req);
    return response.data;
  },

  toggleFundKillSwitch: async (fundId: string, req: KillSwitchRequest): Promise<APIResponse<boolean>> => {
    const response = await apiClient.post<APIResponse<boolean>>(`/api/v1/risk/fund/${fundId}/kill-switch`, req);
    return response.data;
  },

  triggerAiRiskReview: async (fundId: string): Promise<APIResponse<{recommendation: RiskRecommendation}>> => {
    const response = await apiClient.post<APIResponse<{recommendation: RiskRecommendation}>>('/api/v1/risk/ai-review', { fund_id: fundId });
    return response.data;
  },

  applyAiRiskRecommendation: async (fundId: string, recommendation: RiskRecommendation): Promise<APIResponse<FundRiskConfig>> => {
    const response = await apiClient.post<APIResponse<FundRiskConfig>>(`/api/v1/risk/fund/${fundId}/apply-recommendation`, recommendation);
    return response.data;
  },

  getRebalanceHistory: async (fundId?: string, limit: number = 20): Promise<APIResponse<RebalanceHistoryItem[]>> => {
    const params: Record<string, string> = { limit: String(limit) };
    if (fundId) params.fund_id = fundId;
    const response = await apiClient.get<APIResponse<RebalanceHistoryItem[]>>('/api/v1/risk/rebalance-history', { params });
    return response.data;
  }
};
