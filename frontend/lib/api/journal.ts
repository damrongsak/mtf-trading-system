import { apiClient } from './client';
import { JournalEntry, CreateJournalEntryDto, PaginatedResponse, APIResponse, JournalStatsResponse, EquityCurvePoint, PatternAnalysisResponse } from './types';

export interface JournalFilters {
    symbol?: string;
    direction?: string;
    dateFrom?: string;
    dateTo?: string;
    search?: string;
}

/**
 * Get all journal entries for the current user (paginated)
 * @param page - Page number (default: 1)
 * @param perPage - Items per page (default: 10)
 * @param filters - Optional filters
 * @returns Paginated journal entries
 */
export async function getJournalEntries(
    page: number = 1, 
    perPage: number = 10,
    filters?: JournalFilters
): Promise<PaginatedResponse<JournalEntry>> {
    const params: any = { page, per_page: perPage };
    
    if (filters) {
        if (filters.symbol) params.symbol = filters.symbol;
        if (filters.direction && filters.direction !== 'ALL') params.direction = filters.direction;
        if (filters.dateFrom) params.date_from = filters.dateFrom;
        if (filters.dateTo) params.date_to = filters.dateTo;
        if (filters.search) params.search = filters.search;
    }

    const response = await apiClient.get<PaginatedResponse<JournalEntry>>('/api/v1/journal', {
        params
    });
    return response.data;
}

/**
 * Get a single journal entry by ID
 * @param id - Journal entry ID
 * @returns Journal entry data
 */
export async function getJournalEntry(id: string): Promise<JournalEntry> {
    const response = await apiClient.get<APIResponse<JournalEntry>>(`/api/v1/journal/${id}`);

    if (!response.data.data) {
        throw new Error('Invalid response from journal endpoint');
    }

    return response.data.data;
}

/**
 * Create a new journal entry
 * @param data - Journal entry data
 * @returns Created journal entry
 */
export async function createJournalEntry(data: CreateJournalEntryDto): Promise<JournalEntry> {
    const response = await apiClient.post<APIResponse<JournalEntry>>('/api/v1/journal/', data);

    if (!response.data.data) {
        throw new Error('Invalid response from journal endpoint');
    }

    return response.data.data;
}

/**
 * Update an existing journal entry
 * @param id - Journal entry ID
 * @param data - Updated journal entry data
 * @returns Updated journal entry
 */
export async function updateJournalEntry(
    id: string,
    data: Partial<CreateJournalEntryDto>
): Promise<JournalEntry> {
    const response = await apiClient.put<APIResponse<JournalEntry>>(`/api/v1/journal/${id}`, data);

    if (!response.data.data) {
        throw new Error('Invalid response from journal endpoint');
    }

    return response.data.data;
}

/**
 * Delete a journal entry
 * @param id - Journal entry ID
 */
export async function deleteJournalEntry(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/journal/${id}`);
}

/**
 * Get aggregated journal statistics
 */
export async function getJournalStats(): Promise<JournalStatsResponse> {
    const response = await apiClient.get<APIResponse<JournalStatsResponse>>('/api/v1/journal/analytics/stats');
    if (!response.data.data) throw new Error('Invalid stats response');
    return response.data.data;
}

/**
 * Get equity curve data points
 */
export async function getJournalEquityCurve(): Promise<EquityCurvePoint[]> {
    const response = await apiClient.get<APIResponse<EquityCurvePoint[]>>('/api/v1/journal/analytics/equity');
    if (!response.data.data) throw new Error('Invalid equity response');
    return response.data.data;
}

/**
 * Get pattern analysis data
 */
export async function getPatternAnalysis(): Promise<PatternAnalysisResponse> {
    const response = await apiClient.get<APIResponse<PatternAnalysisResponse>>('/api/v1/journal/analytics/patterns');
    if (!response.data.data) throw new Error('Invalid pattern response');
    return response.data.data;
}
