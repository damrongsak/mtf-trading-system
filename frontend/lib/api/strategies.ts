import { apiClient } from './client';
import {
  StrategyResponse,
  StrategyCreate,
  LogicTemplate,
  APIResponse,
  StrategyBacktestRequest,
  StrategyBacktestResponse
} from './types';

export const getStrategies = async (): Promise<StrategyResponse[]> => {
  const response = await apiClient.get<APIResponse<StrategyResponse[]>>('/api/v1/strategies');
  return response.data.data || [];
};

export const getStrategyTemplates = async (): Promise<LogicTemplate[]> => {
  const response = await apiClient.get<APIResponse<LogicTemplate[]>>('/api/v1/strategies/templates');
  return response.data.data || [];
};

export const createStrategy = async (data: StrategyCreate): Promise<StrategyResponse> => {
  const response = await apiClient.post<APIResponse<StrategyResponse>>('/api/v1/strategies', data);
  return response.data.data!;
};

export const startStrategy = async (id: string): Promise<APIResponse<{ status: string }>> => {
  const response = await apiClient.post<APIResponse<{ status: string }>>(`/api/v1/strategies/${id}/start`, {});
  return response.data;
};

export const stopStrategy = async (id: string): Promise<APIResponse<{ status: string }>> => {
  const response = await apiClient.post<APIResponse<{ status: string }>>(`/api/v1/strategies/${id}/stop`, {});
  return response.data;
};

export const deleteStrategy = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/strategies/${id}`);
};

export const validateStrategy = async (data: StrategyBacktestRequest): Promise<StrategyBacktestResponse> => {
  const response = await apiClient.post<APIResponse<StrategyBacktestResponse>>('/api/v1/strategies/backtest-custom', data);
  return response.data.data!;
};

export const saveCustomStrategy = async (data: StrategyCreate): Promise<StrategyResponse> => {
  return createStrategy(data);
};
