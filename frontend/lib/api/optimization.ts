import { apiClient } from './client';
import {
    BacktestRequest,
    OptimizationResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    APIResponse
} from './types';

export * from './types';

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
