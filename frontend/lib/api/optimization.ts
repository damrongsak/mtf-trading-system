import { apiClient } from './client';
import { BacktestRequest } from './backtest';

export interface SensitivityMetrics {
    p95: number;
    median: number;
    worst?: number;
    best?: number;
}

export interface MonteCarloResponse {
    iterations: number;
    max_drawdown: SensitivityMetrics;
    total_return: SensitivityMetrics;
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

export interface MonteCarloRequest {
    trades: Record<string, unknown>[]; // Trade objects
    iterations?: number;
}

import { APIResponse } from './types';

export async function runOptimization(req: BacktestRequest): Promise<OptimizationResponse> {
    const response = await apiClient.post<APIResponse<OptimizationResponse>>('/api/v1/backtest/optimize', req);
    if (!response.data.data) {
        throw new Error('No data received from optimization endpoint');
    }
    return response.data.data;
}

export async function runMonteCarlo(req: MonteCarloRequest): Promise<MonteCarloResponse> {
    const response = await apiClient.post<APIResponse<MonteCarloResponse>>('/api/v1/backtest/monte-carlo', req);
    if (!response.data.data) {
        throw new Error('No data received from Monte Carlo endpoint');
    }
    return response.data.data;
}
