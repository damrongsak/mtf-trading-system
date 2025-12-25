import { apiClient } from './client';
import { BacktestRequest, BacktestResponse, StrategyBacktestRequest, APIResponse } from './types';

export type { BacktestRequest, BacktestResponse, StrategyBacktestRequest };

export async function runBacktest(payload: BacktestRequest): Promise<BacktestResponse> {
  const response = await apiClient.post<APIResponse<BacktestResponse>>('/api/v1/backtest/run', payload);
  if (!response.data.data) {
    throw new Error('Invalid server response: Missing data');
  }
  return response.data.data;
}

export async function runCustomBacktest(payload: StrategyBacktestRequest): Promise<BacktestResponse> {
  const response = await apiClient.post<APIResponse<BacktestResponse>>('/api/v1/backtest/custom', payload);
  if (!response.data.data) {
    throw new Error('Invalid server response: Missing data');
  }
  return response.data.data;
}
