import { apiClient } from './client';
import { APIResponse } from './types';

export interface MarketAnalysisRequest {
    trend_4h: string;
    current_price: number;
    key_levels: number[];
    recent_signals: unknown[];
}

export interface JournalAnalysisRequest {
    entry_content: string;
    entry_id?: string;
}

export interface AnalysisResponse {
    insight: string;
    timestamp: string;
}

export async function getMarketAnalysis(data: MarketAnalysisRequest): Promise<AnalysisResponse> {
    const response = await apiClient.post<APIResponse<AnalysisResponse>>('/api/v1/ai/market-analysis', data);
    if (!response.data.data) {
        throw new Error('No analysis data received');
    }
    return response.data.data;
}

export async function getJournalAnalysis(data: JournalAnalysisRequest): Promise<AnalysisResponse> {
    const response = await apiClient.post<APIResponse<AnalysisResponse>>('/api/v1/ai/journal-analysis', data);
    if (!response.data.data) {
        throw new Error('No analysis data received');
    }
    return response.data.data;
}
