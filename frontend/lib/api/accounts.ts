import { apiClient } from './client';
import { APIResponse } from './types';

export interface BrokerAccount {
    id: string;
    broker_name: string;
    account_name: string;
    account_number?: string;
    is_active: boolean;
    is_live: boolean;
    created_at: string;
}

export interface CreateAccountDto {
    broker_name: string;
    account_name: string;
    account_number?: string;
    is_live: boolean;
    credentials: Record<string, any>;
}

export async function getBrokerAccounts(): Promise<BrokerAccount[]> {
    const response = await apiClient.get<APIResponse<BrokerAccount[]>>('/api/v1/accounts/');
    return response.data.data || [];
}

export async function createBrokerAccount(data: CreateAccountDto): Promise<BrokerAccount> {
    const response = await apiClient.post<APIResponse<BrokerAccount>>('/api/v1/accounts/', data);
    return response.data.data!;
}

export async function deleteBrokerAccount(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/accounts/${id}`);
}
