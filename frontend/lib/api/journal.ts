import { apiClient } from './client';
import { JournalEntry, CreateJournalEntryDto, PaginatedResponse, APIResponse } from './types';

/**
 * Get all journal entries for the current user (paginated)
 * @param page - Page number (default: 1)
 * @param perPage - Items per page (default: 10)
 * @returns Paginated journal entries
 */
export async function getJournalEntries(page: number = 1, perPage: number = 10): Promise<PaginatedResponse<JournalEntry>> {
    const response = await apiClient.get<PaginatedResponse<JournalEntry>>('/api/v1/journal', {
        params: { page, per_page: perPage }
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
