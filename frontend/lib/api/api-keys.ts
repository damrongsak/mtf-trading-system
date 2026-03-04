import { api } from './index';

export interface ApiKeyResponse {
    id: string;
    name: string;
    api_key: string;
    api_secret?: string; // Only on creation
    is_active: boolean;
    created_at: string;
    last_used_at?: string;
}

export const getApiKeys = async (): Promise<ApiKeyResponse[]> => {
    const response = await api.get('/api-keys');
    return response.data;
};

export const createApiKey = async (name: string): Promise<ApiKeyResponse> => {
    const response = await api.post('/api-keys', { name });
    return response.data;
};

export const deleteApiKey = async (id: string): Promise<void> => {
    await api.delete(`/api-keys/${id}`);
};
