import { apiClient } from './client';

export interface SystemConfig {
    supported_timeframes: string[];
    [key: string]: any;
}

export async function fetchSystemConfig(): Promise<SystemConfig> {
    const response = await apiClient.get<SystemConfig>('/api/v1/system/config');
    return response.data;
}
