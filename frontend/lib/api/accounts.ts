import { apiClient } from './client';
import {
    BrokerAccount,
    BrokerAccountCreate,
    BrokerAccountUpdate,
    APIResponse
} from './types';

export const getAccounts = async (): Promise<BrokerAccount[]> => {
    // The backend returns APIResponse<List<BrokerAccountResponse>>
    const response = await apiClient.get<APIResponse<BrokerAccount[]> | BrokerAccount[]>('/api/v1/accounts/');

    // Handle wrapper if present
    if ('data' in response.data && Array.isArray(response.data.data)) {
        return response.data.data;
    }
    return response.data as BrokerAccount[];
};

export const createAccount = async (data: BrokerAccountCreate): Promise<BrokerAccount> => {
    const response = await apiClient.post<APIResponse<BrokerAccount>>('/api/v1/accounts/', data);
    if (response.data.data) {
        return response.data.data;
    }
    return response.data as unknown as BrokerAccount;
};

export const updateAccount = async (id: string, data: BrokerAccountUpdate): Promise<BrokerAccount> => {
    const response = await apiClient.put<APIResponse<BrokerAccount>>(`/api/v1/accounts/${id}`, data);
    if (response.data.data) {
        return response.data.data;
    }
    return response.data as unknown as BrokerAccount;
};

export const deleteAccount = async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/accounts/${id}`);
};

export const fetchBrokerSymbols = async (id: string): Promise<string[]> => {
    const response = await apiClient.post<APIResponse<string[]>>(`/api/v1/accounts/${id}/fetch-symbols`);
    if (response.data.data) {
        return response.data.data;
    }
    return [];
};

export const refreshBrokerToken = async (id: string): Promise<void> => {
    await apiClient.post(`/api/v1/accounts/${id}/refresh-token`);
};
