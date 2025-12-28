import { apiClient } from './client';
import { BacktestRequest, BacktestResponse, StrategyBacktestRequest, APIResponse, OptimizationResult, OptimizationResponse } from './types';

export type { BacktestRequest, BacktestResponse, StrategyBacktestRequest, OptimizationResult, OptimizationResponse };

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





export async function runOptimization(payload: StrategyBacktestRequest): Promise<OptimizationResult[]> {
  const response = await apiClient.post<APIResponse<OptimizationResponse>>('/api/v1/backtest/optimize', payload);
  if (!response.data.data) {
    throw new Error('Invalid server response: Missing data');
  }
  return response.data.data.results;
}

import { MonteCarloRequest, MonteCarloResponse } from './types';

export async function runMonteCarlo(payload: MonteCarloRequest): Promise<MonteCarloResponse> {
  const response = await apiClient.post<APIResponse<MonteCarloResponse>>('/api/v1/backtest/monte-carlo', payload);
  if (!response.data.data) {
    throw new Error('Invalid server response: Missing data');
  }
  return response.data.data;
}
