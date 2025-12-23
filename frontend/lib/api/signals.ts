import { apiClient } from './client';
import { APIResponse, Signal } from './types';

/**
 * Get the latest signal for a symbol
 */
export async function getLatestSignal(symbol: string): Promise<Signal> {
    const response = await apiClient.get<APIResponse<Signal>>(`/api/v1/signal/latest/${symbol}`);
    return response.data.data!;
}

/**
 * Trigger a manual signal check
 */
export async function checkSignal(symbol: string): Promise<Signal> {
    const response = await apiClient.post<APIResponse<Signal>>('/api/v1/signal/check', null, {
        params: { symbol }
    });
    return response.data.data!;
}

/**
 * Batch fetch signals for all active symbols of a broker
 */
export async function getBatchSignals(broker: string = "OANDA"): Promise<Signal[]> {
    const response = await apiClient.post<APIResponse<Signal[]>>('/api/v1/signal/batch', { broker });
    return response.data.data || [];
}
