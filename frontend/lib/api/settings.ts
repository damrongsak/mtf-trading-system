import { apiClient } from './client';
import { APIResponse, UserPreferences, UpdatePreferencesDto } from './types';

/**
 * Get current user's preferences
 * Creates default preferences if none exist
 */
export async function getPreferences(): Promise<UserPreferences> {
    const response = await apiClient.get<APIResponse<UserPreferences>>('/api/v1/settings/preferences');

    if (!response.data.data) {
        throw new Error('Invalid response from preferences endpoint');
    }

    return response.data.data;
}

/**
 * Update user preferences
 * @param data - Preference update data
 */
export async function updatePreferences(data: UpdatePreferencesDto): Promise<UserPreferences> {
    const response = await apiClient.put<APIResponse<UserPreferences>>('/api/v1/settings/preferences', data);

    if (!response.data.data) {
        throw new Error('Invalid response from preferences update endpoint');
    }

    return response.data.data;
}
