import { apiClient } from './client';
import { APIResponse, Signal } from './types';

/**
 * Get the latest signal for a symbol
 */
export async function getLatestSignal(symbol: string): Promise<Signal> {
    const response = await apiClient.get<APIResponse<Signal>>(`/signal/latest/${symbol}`);
    return response.data.data!;
}

/**
 * Trigger a manual signal check
 */
export async function checkSignal(symbol: string): Promise<Signal> {
    const response = await apiClient.post<APIResponse<Signal>>('/signal/check', null, {
        params: { symbol }
    });
    return response.data.data!;
}
