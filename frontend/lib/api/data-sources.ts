import { apiClient } from './client';
import { APIResponse, DataSource, DataSourceCreate, DataSourceUpdate, DataSourceType, DataSourceProvider } from './types';

export type { DataSource, DataSourceCreate, DataSourceUpdate, DataSourceType, DataSourceProvider };

export async function getDataSources(): Promise<DataSource[]> {
    const response = await apiClient.get<APIResponse<DataSource[]>>('/api/v1/data-sources');
    return response.data.data || [];
}

export async function getDataSource(id: string): Promise<DataSource> {
    const response = await apiClient.get<APIResponse<DataSource>>(`/api/v1/data-sources/${id}`);
    if (!response.data.data) throw new Error("No data returned");
    return response.data.data;
}

export async function createDataSource(data: DataSourceCreate): Promise<DataSource> {
    const response = await apiClient.post<APIResponse<DataSource>>('/api/v1/data-sources', data);
    if (!response.data.data) throw new Error("No data returned");
    return response.data.data;
}

export async function updateDataSource(id: string, data: DataSourceUpdate): Promise<DataSource> {
    const response = await apiClient.put<APIResponse<DataSource>>(`/api/v1/data-sources/${id}`, data);
    if (!response.data.data) throw new Error("No data returned");
    return response.data.data;
}

export async function deleteDataSource(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/data-sources/${id}`);
}

export async function triggerBackfill(id: string, params: { symbol: string, timeframe: string, count: number }): Promise<void> {
    await apiClient.post(`/api/v1/data-sources/${id}/backfill`, params);
}

export async function fetchDataSourceSymbols(id: string): Promise<string[]> {
    const response = await apiClient.get<APIResponse<string[]>>(`/api/v1/data-sources/${id}/symbols`);
    return response.data.data || [];
}
