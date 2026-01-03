import { apiClient } from './client';
import { OpportunityLog } from './types';

export async function getOpportunities(limit: number = 50): Promise<OpportunityLog[]> {
    const response = await apiClient.get<OpportunityLog[]>('/api/v1/analysis/opportunities', { params: { limit } });
    return response.data;
}


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

export interface AtrParams {
    high: number[];
    low: number[];
    close: number[];
    window?: number;
}

export async function calculateATR(params: AtrParams): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/atr', params);
    return response.data.values as number[];
}

export interface MacdParams {
    close: number[];
    fast?: number;
    slow?: number;
    signal?: number;
}

export interface MacdResponse {
    macd: (number | null)[];
    signal: (number | null)[];
    hist: (number | null)[];
}

export async function calculateMACD(params: MacdParams): Promise<MacdResponse> {
    const response = await apiClient.post<MacdResponse>('/api/v1/analysis/calculate/macd', params);
    return response.data;
}

export interface AdxParams {
    high: number[];
    low: number[];
    close: number[];
    length?: number;
}

export interface AdxResponse {
    adx: (number | null)[];
    dmp: (number | null)[];
    dmn: (number | null)[];
}

export async function calculateADX(params: AdxParams): Promise<AdxResponse> {
    const response = await apiClient.post<AdxResponse>('/api/v1/analysis/calculate/adx', params);
    return response.data;
}
