import { apiClient } from './client';
import {
  StrategyResponse,
  StrategyCreate,
  LogicTemplate,
  APIResponse,
  PaginatedResponse
} from './types';

export const getStrategies = async (): Promise<StrategyResponse[]> => {
  // Can return array or paginated response depending on backend config
  const response = await apiClient.get<PaginatedResponse<StrategyResponse> | StrategyResponse[]>('/api/v1/strategies');

  if ('data' in response.data && Array.isArray(response.data.data)) {
    return response.data.data;
  }
  return response.data as StrategyResponse[];
};

export const getStrategyTemplates = async (): Promise<LogicTemplate[]> => {
  const response = await apiClient.get<APIResponse<LogicTemplate[]> | LogicTemplate[]>('/api/v1/strategies/templates');

  if ('data' in response.data && Array.isArray(response.data.data)) {
    return response.data.data;
  }
  return response.data as LogicTemplate[];
};

export const createStrategy = async (data: StrategyCreate): Promise<StrategyResponse> => {
  const response = await apiClient.post<StrategyResponse>('/api/v1/strategies', data);
  return response.data;
};

export const startStrategy = async (id: string): Promise<APIResponse<{ status: string }>> => {
  const response = await apiClient.post<{ status: string }>(`/api/v1/strategies/${id}/start`, {});
  return {
    status: response.status as any, // Enum mapping might be needed if strict
    timestamp: new Date().toISOString(),
    data: response.data
  };
};

export const stopStrategy = async (id: string): Promise<APIResponse<{ status: string }>> => {
  const response = await apiClient.post<{ status: string }>(`/api/v1/strategies/${id}/stop`, {});
  return {
    status: response.status as any,
    timestamp: new Date().toISOString(),
  };
};

export const deleteStrategy = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/strategies/${id}`);
};

export const validateStrategy = async (data: any): Promise<any> => {
  // Mock for now, replace with actual endpoint
  const response = await apiClient.post<any>('/api/v1/strategies/backtest-custom', data);
  return response.data;
};

export const saveCustomStrategy = async (data: StrategyCreate): Promise<StrategyResponse> => {
  return createStrategy(data);
};
