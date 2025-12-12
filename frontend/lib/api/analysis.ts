import { apiClient } from './client';

export interface IndicatorResponse {
    values: (number | null)[];
}

export interface EmaParams {
    data: number[];
    span?: number;
}

export interface RsiParams {
    close: number[];
    window?: number;
}

export async function calculateEMA(params: EmaParams): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/ema', params);
    // Filter nulls or handle them? Lightweight charts handles whitespace/nulls by just not drawing? 
    // Actually usually we need to pass time+value.
    // We will return the raw array including nulls.
    return response.data.values as number[];
}

export async function calculateRSI(params: RsiParams): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/rsi', params);
    return response.data.values as number[];
}
