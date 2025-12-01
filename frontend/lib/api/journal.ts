import { apiClient } from './client';
import { JournalEntry, CreateJournalEntryDto } from './types';

/**
 * Get all journal entries for the current user
 * @returns Array of journal entries
 */
export async function getJournalEntries(): Promise<JournalEntry[]> {
    const response = await apiClient.get<JournalEntry[]>('/api/v1/journal');
    return response.data;
}

/**
 * Get a single journal entry by ID
 * @param id - Journal entry ID
 * @returns Journal entry data
 */
export async function getJournalEntry(id: string): Promise<JournalEntry> {
    const response = await apiClient.get<JournalEntry>(`/api/v1/journal/${id}`);
    return response.data;
}

/**
 * Create a new journal entry
 * @param data - Journal entry data
 * @returns Created journal entry
 */
export async function createJournalEntry(data: CreateJournalEntryDto): Promise<JournalEntry> {
    const response = await apiClient.post<JournalEntry>('/api/v1/journal/', data);
    return response.data;
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
    const response = await apiClient.put<JournalEntry>(`/api/v1/journal/${id}`, data);
    return response.data;
}

/**
 * Delete a journal entry
 * @param id - Journal entry ID
 */
export async function deleteJournalEntry(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/journal/${id}`);
}
