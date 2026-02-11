import { apiClient } from './client';
import {
    BrokerAccount,
    BrokerAccountCreate,
    BrokerAccountUpdate,
    APIResponse
} from './types';
import { AccountSummary } from './execution';

export const getAccounts = async (): Promise<BrokerAccount[]> => {
    const response = await apiClient.get<APIResponse<BrokerAccount[]>>('/api/v1/accounts/');
    return response.data.data || [];
};

export const createAccount = async (data: BrokerAccountCreate): Promise<BrokerAccount> => {
    const response = await apiClient.post<APIResponse<BrokerAccount>>('/api/v1/accounts/', data);
    return response.data.data!;
}

export const updateAccount = async (id: string, data: BrokerAccountUpdate): Promise<BrokerAccount> => {
    const response = await apiClient.put<APIResponse<BrokerAccount>>(`/api/v1/accounts/${id}`, data);
    return response.data.data!;
}

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

export const testAccountConnection = async (id: string): Promise<APIResponse<AccountSummary>> => {
    const response = await apiClient.get<APIResponse<AccountSummary>>(`/api/v1/execution/account/summary`, {
        params: { account_id: id }
    });
    return response.data;
};
