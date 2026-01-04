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
