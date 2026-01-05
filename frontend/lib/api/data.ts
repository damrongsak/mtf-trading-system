import { apiClient } from './client';

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

    const response = await apiClient.post<OpenInterestImportResult>('/api/v1/data/open-interest/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
}

export interface OpenInterestSnapshot {
    snapshot_at: string;
    count: number;
    created_at: string;
}

export async function getOpenInterestSnapshots(limit: number = 20): Promise<OpenInterestSnapshot[]> {
    const response = await apiClient.get<OpenInterestSnapshot[]>('/api/v1/data/open-interest/snapshots', {
        params: { limit }
    });
    return response.data;
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

    const response = await apiClient.get<OpenInterestRecord[]>('/api/v1/data/open-interest/details', {
        params
    });
    return response.data;
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

    const response = await apiClient.get<OpenInterestAnalysis>('/api/v1/data/open-interest/analysis', {
        params
    });
    return response.data;
}

export async function getOpenInterestContracts(snapshotAt: string): Promise<string[]> {
    const response = await apiClient.get<string[]>('/api/v1/data/open-interest/contracts', {
        params: { snapshot_at: snapshotAt }
    });
    return response.data;
}
