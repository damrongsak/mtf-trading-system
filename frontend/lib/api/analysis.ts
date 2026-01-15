import { apiClient } from './client';
import { OpportunityLog } from './types';
import {
    EmaRequest,
    RsiRequest,
    AtrRequest,
    MacdRequest,
    MacdResponse,
    AdxRequest,
    AdxResponse,
    SMCRequest,
    SMCResponse,
    IndicatorResponse,
    AnalysisDriftPost200Response
} from './generated/api';

export * from './generated/api';

export async function getOpportunities(limit: number = 50): Promise<OpportunityLog[]> {
    const response = await apiClient.get<OpportunityLog[]>('/api/v1/analysis/opportunities', { params: { limit } });
    return response.data;
}

export async function calculateEMA(params: EmaRequest): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/ema', params);
    // Return values or empty array if undefined
    return response.data.values ?? [];
}

export async function calculateRSI(params: RsiRequest): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/rsi', params);
    return response.data.values ?? [];
}

export async function calculateATR(params: AtrRequest): Promise<number[]> {
    const response = await apiClient.post<IndicatorResponse>('/api/v1/analysis/calculate/atr', params);
    return response.data.values ?? [];
}

export async function calculateMACD(params: MacdRequest): Promise<MacdResponse> {
    const response = await apiClient.post<MacdResponse>('/api/v1/analysis/calculate/macd', params);
    return response.data;
}

export async function calculateADX(params: AdxRequest): Promise<AdxResponse> {
    const response = await apiClient.post<AdxResponse>('/api/v1/analysis/calculate/adx', params);
    return response.data;
}

export async function getDriftAnalysis(windowHours: number = 24): Promise<AnalysisDriftPost200Response> {
    // Note: The generated client uses analysisDriftPost but here we use apiClient direct call to match existing pattern.
    // The endpoint is /api/v1/analysis/drift [POST]
    const response = await apiClient.post<AnalysisDriftPost200Response>('/api/v1/analysis/drift', { window_hours: windowHours });
    return response.data;
}

export async function calculateSMC(params: SMCRequest): Promise<SMCResponse> {
    const response = await apiClient.post<SMCResponse>('/api/v1/analysis/calculate/smc', params);
    return response.data;
}
