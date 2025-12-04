import { apiClient } from './client';
import { APIResponse, Fund } from './types';

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
