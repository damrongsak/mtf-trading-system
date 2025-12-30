import { apiClient } from './client';
import { APIResponse, Fund, StrategyType, AssetClass } from './types';

/**
 * Get all funds the current user has access to
 */
export async function getFunds(): Promise<Fund[]> {
    const response = await apiClient.get<APIResponse<Fund[]>>('/api/v1/funds');

    if (!response.data.data) {
        throw new Error('Invalid response from funds endpoint');
    }

    return response.data.data;
}

/**
 * Get details of a specific fund
 * @param fundId - Fund ID
 */
export async function getFund(fundId: string): Promise<Fund> {
    const response = await apiClient.get<APIResponse<Fund>>(`/api/v1/funds/${fundId}`);

    if (!response.data.data) {
        throw new Error('Invalid response from fund endpoint');
    }

    return response.data.data;
}

export interface CreateFundDto {
    name: string;
    description?: string;
}

export interface UpdateFundDto {
    name?: string;
    description?: string;
    strategy_type?: StrategyType;
    asset_classes?: AssetClass[];
    max_risk_per_trade?: number;
    default_lot_size?: number;
    max_drawdown_threshold?: number | null;
    max_portfolio_beta?: number | null;
    gross_exposure_limit?: number | null;
    net_exposure_limit?: number | null;
    position_limit_single?: number | null;
    position_limit_sector?: number | null;
}

/**
 * Create a new fund
 */
export async function createFund(data: CreateFundDto): Promise<Fund> {
    const response = await apiClient.post<APIResponse<Fund>>('/api/v1/funds', data);

    if (!response.data.data) {
        throw new Error('Invalid response from create fund endpoint');
    }

    return response.data.data;
}

/**
 * Update a fund
 */
export async function updateFund(fundId: string, data: UpdateFundDto): Promise<Fund> {
    const response = await apiClient.put<APIResponse<Fund>>(`/api/v1/funds/${fundId}`, data);

    if (!response.data.data) {
        throw new Error('Invalid response from update fund endpoint');
    }

    return response.data.data;
}

/**
 * Delete a fund
 */
export async function deleteFund(fundId: string): Promise<void> {
    await apiClient.delete(`/api/v1/funds/${fundId}`);
}
