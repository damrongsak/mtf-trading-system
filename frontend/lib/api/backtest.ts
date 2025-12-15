import { apiClient } from './client';
import { BacktestRequest, BacktestResponse } from './types';

export type { BacktestRequest, BacktestResponse };

export async function runBacktest(payload: BacktestRequest): Promise<BacktestResponse> {
  const response = await apiClient.post<BacktestResponse>('/api/v1/backtest/run', payload);
  return response.data;
}
