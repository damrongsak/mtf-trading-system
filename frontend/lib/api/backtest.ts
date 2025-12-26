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

export interface OptimizationResult {
  params: Record<string, string | number | boolean>;
  metrics: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    total_trades: number;
  };
}

export interface OptimizationResponse {
  results: OptimizationResult[];
}


export async function runOptimization(payload: StrategyBacktestRequest): Promise<OptimizationResult[]> {
  const response = await apiClient.post<OptimizationResponse>('/api/v1/backtest/optimize', payload);
  return response.data.results;
}

import { MonteCarloRequest, MonteCarloResponse } from './types';

export async function runMonteCarlo(payload: MonteCarloRequest): Promise<MonteCarloResponse> {
  const response = await apiClient.post<MonteCarloResponse>('/api/v1/backtest/monte-carlo', payload);
  return response.data;
}
