import { apiClient } from './client';
import { APIResponse } from './types';

export interface OpenInterestImportResult {
    status: string;
    records_processed: number;
    snapshot_at: string;
}

export async function uploadOpenInterest(file: File, snapshotAt?: Date): Promise<OpenInterestImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (snapshotAt) {
        formData.append('snapshot_at', snapshotAt.toISOString());
    }

    const response = await apiClient.post<APIResponse<OpenInterestImportResult>>('/api/v1/data/open-interest/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data.data!;
}

export interface OpenInterestSnapshot {
    snapshot_at: string;
    count: number;
    created_at: string;
}

export async function getOpenInterestSnapshots(limit: number = 20): Promise<OpenInterestSnapshot[]> {
    const response = await apiClient.get<APIResponse<OpenInterestSnapshot[]>>('/api/v1/data/open-interest/snapshots', {
        params: { limit }
    });
    return response.data.data || [];
}

export interface OpenInterestRecord {
    contract_symbol: string;
    dte: number;
    strike: number;
    call_oi: number;
    put_oi: number;
}

export async function getOpenInterestDetails(
    snapshotAt: string,
    contract?: string,
    minOi?: number,
    maxOi?: number,
    smartFilter?: boolean
): Promise<OpenInterestRecord[]> {
    const params: Record<string, string | number | boolean> = { snapshot_at: snapshotAt };
    if (contract) params.contract = contract;
    if (minOi && minOi > 0) params.min_oi = minOi;
    if (maxOi) params.max_oi = maxOi;
    if (smartFilter) params.smart_filter = smartFilter;

    const response = await apiClient.get<APIResponse<OpenInterestRecord[]>>('/api/v1/data/open-interest/details', {
        params
    });
    return response.data.data || [];
}

export interface OpenInterestAnalysis {
    summary: {
        total_call_oi: number;
        total_put_oi: number;
        pcr: number;
        max_call_strike: number;
        max_put_strike: number;
    };
    distribution: {
        strike: number;
        call_oi: number;
        put_oi: number;
        net_delta: number;
    }[];
}

export async function getOpenInterestAnalysis(
    snapshotAt?: string,
    contract?: string,
    minOi?: number,
    maxOi?: number
): Promise<OpenInterestAnalysis> {
    const params: Record<string, string | number | boolean> = { snapshot_at: snapshotAt || '' };
    if (contract) params.contract = contract;
    if (minOi && minOi > 0) params.min_oi = minOi;
    if (maxOi) params.max_oi = maxOi;

    const response = await apiClient.get<APIResponse<OpenInterestAnalysis>>('/api/v1/data/open-interest/analysis', {
        params
    });
    return response.data.data!;
}

export async function getOpenInterestContracts(snapshotAt: string): Promise<string[]> {
    const response = await apiClient.get<APIResponse<string[]>>('/api/v1/data/open-interest/contracts', {
        params: { snapshot_at: snapshotAt }
    });
    return response.data.data || [];
}

export interface MarketFeature {
    symbol: string;
    timeframe: string;
    timestamp: string;
    close: number;
    rsi_14?: number | null;
    atr_14?: number | null;
    ema_9?: number | null;
    ema_20?: number | null;
    ema_50?: number | null;
    ema_200?: number | null;
    volatility?: number | null;
    macd?: number | null;
    macd_signal?: number | null;
    macd_hist?: number | null;
    bb_upper?: number | null;
    bb_middle?: number | null;
    bb_lower?: number | null;
    adx?: number | null;
    di_plus?: number | null;
    di_minus?: number | null;
    high_20?: number | null;
    low_20?: number | null;
    swing_high?: number | null;
    swing_low?: number | null;
    smc?: unknown;
    [key: string]: unknown;
}

export async function getMarketFeatures(): Promise<MarketFeature[]> {
    const response = await apiClient.get<APIResponse<MarketFeature[]>>('/api/v1/data/features');
    return response.data.data || [];
}
