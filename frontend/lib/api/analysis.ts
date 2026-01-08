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

export interface DriftAnalysisResponse {
    status: 'HEALTHY' | 'MONITORING' | 'DRIFT_WARNING' | 'INACTIVE';
    filter_rate: number;
    signal_count?: number;
    opportunity_count?: number;
    top_rejection_reason?: string;
    window_hours?: number;
}

export async function getDriftAnalysis(window_hours: number = 24): Promise<DriftAnalysisResponse> {
    const response = await apiClient.post<DriftAnalysisResponse>('/api/v1/analysis/drift', null, { params: { window_hours } });
    return response.data;
}

export interface SMCParams {
    open: number[];
    high: number[];
    low: number[];
    close: number[];
    volume?: number[];
}

export interface SMCOrderBlock {
    type: 'bullish' | 'bearish';
    index: number;
    top: number;
    bottom: number;
    mitigated: boolean;
    strength: string;
}

export interface SMCFVG {
    type: 'bullish' | 'bearish';
    index: number;
    top: number;
    bottom: number;
    mitigated: boolean;
}

export interface SMCSweep {
    type: 'bullish_sweep' | 'bearish_sweep';
    index: number;
    level: number;
    description: string;
}

export interface SMCStructureLabel {
    index: number;
    text: string;
    price: number;
}

export interface SMCStructure {
    pivots?: Array<{ index: number, type: string, price: number }>;
    labels?: SMCStructureLabel[];
    events?: Array<{ index: number, type: string, direction: string }>;
}

export interface SMCResponse {
    order_blocks: SMCOrderBlock[];
    fvgs: SMCFVG[];
    liquidity_sweeps: SMCSweep[];
    structure: SMCStructure;
    auto_fibs: Record<string, number>;
}

export async function calculateSMC(params: SMCParams): Promise<SMCResponse> {
    const response = await apiClient.post<SMCResponse>('/api/v1/analysis/calculate/smc', params);
    return response.data;
}
