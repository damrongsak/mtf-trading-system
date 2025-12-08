import { apiClient } from './client';
import { APIResponse, PaginatedResponse, BacktestRequest, BacktestResponse, BacktestConfig, BacktestHistorySummary } from './types';

const BASE_PATH = '/api/v1/backtest';

export async function runBacktest(data: BacktestRequest): Promise<BacktestResponse> {
    const response = await apiClient.post<APIResponse<BacktestResponse>>(`${BASE_PATH}/run`, data);
    if (!response.data.data) {
        throw new Error('No data returned from backtest run');
    }
    return response.data.data;
}

export async function saveBacktestConfig(data: { name: string; description?: string; config: BacktestRequest }): Promise<BacktestConfig> {
    const response = await apiClient.post<APIResponse<BacktestConfig>>(`${BASE_PATH}/configs`, data);
    if (!response.data.data) throw new Error('Failed to save config');
    return response.data.data;
}

export async function getBacktestConfigs(): Promise<BacktestConfig[]> {
    const response = await apiClient.get<APIResponse<BacktestConfig[]>>(`${BASE_PATH}/configs`);
    return response.data.data || [];
}

export async function getBacktestHistory(page: number = 1, perPage: number = 20): Promise<PaginatedResponse<BacktestHistorySummary>> {
    const response = await apiClient.get<PaginatedResponse<BacktestHistorySummary>>(`${BASE_PATH}/history`, {
        params: { page, per_page: perPage }
    });
    return response.data;
}
