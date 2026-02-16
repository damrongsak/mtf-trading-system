
import { apiClient } from './client';
import { APIResponse, Signal, RecentSignal } from './types';

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
export async function getBatchSignals(broker: string = "CTRADER"): Promise<Signal[]> {
    const response = await apiClient.post<APIResponse<Signal[]>>('/api/v1/signal/batch', { broker });
    return response.data.data || [];
}

/**
 * Get detected signals history from database
 */
export async function getDetectedSignals(limit: number = 20, status?: string): Promise<Signal[]> {
    const params: any = { limit };
    if (status) params.status = status;

    const response = await apiClient.get<APIResponse<Signal[]>>('/api/v1/signal/detected', {
        params
    });
    return response.data.data || [];
}

/**
 * Approve a pending signal
 */
export async function approveSignal(signalId: string): Promise<void> {
    await apiClient.post(`/api/v1/signals/${signalId}/approve`);
}

/**
 * Reject a pending signal
 */
export async function rejectSignal(signalId: string): Promise<void> {
    await apiClient.post(`/api/v1/signals/${signalId}/reject`);
}

/**
 * Reject all pending signals
 */
export async function rejectAllSignals(): Promise<{ cancelled: number }> {
    const response = await apiClient.post<APIResponse<{ cancelled: number }>>('/api/v1/signal/cancel-all');
    // Note: Backend returns data wrapped in APIResponse
    return response.data.data!;
}
