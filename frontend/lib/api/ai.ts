import { apiClient } from './client';

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
    const response = await apiClient.post<AnalysisResponse>('/api/v1/ai/market-analysis', data);
    return response.data;
}

export async function getJournalAnalysis(data: JournalAnalysisRequest): Promise<AnalysisResponse> {
    const response = await apiClient.post<AnalysisResponse>('/api/v1/ai/journal-analysis', data);
    return response.data;
}
