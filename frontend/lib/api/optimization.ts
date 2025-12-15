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
    metrics: Record<string, number>;
}

export interface OptimizationResponse {
    results: OptimizationResult[];
}

export interface MonteCarloRequest {
    trades: Record<string, unknown>[]; // Trade objects
    iterations?: number;
}

export async function runOptimization(req: BacktestRequest): Promise<OptimizationResponse> {
    const response = await apiClient.post<OptimizationResponse>('/api/v1/backtest/optimize', req);
    return response.data;
}

export async function runMonteCarlo(req: MonteCarloRequest): Promise<MonteCarloResponse> {
    const response = await apiClient.post<MonteCarloResponse>('/api/v1/backtest/monte-carlo', req);
    return response.data;
}
