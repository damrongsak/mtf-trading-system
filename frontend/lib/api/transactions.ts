import { apiClient } from './client';
import { Transaction, CreateTransactionDto, BalanceResponse, PaginatedResponse, APIResponse } from './types';

/**
 * Get all transactions for a specific fund (paginated)
 * @param fundId - Fund ID
 * @param page - Page number (default: 1)
 * @param perPage - Items per page (default: 10)
 * @returns Paginated transactions
 */
export async function getTransactions(
    fundId: string,
    page: number = 1,
    perPage: number = 10
): Promise<PaginatedResponse<Transaction>> {
    const response = await apiClient.get<PaginatedResponse<Transaction>>('/api/v1/transactions', {
        params: { fund_id: fundId, page, per_page: perPage }
    });
    return response.data;
}

/**
 * Create a new transaction
 * @param data - Transaction data
 * @returns Created transaction
 */
export async function createTransaction(data: CreateTransactionDto): Promise<Transaction> {
    const response = await apiClient.post<APIResponse<Transaction>>('/api/v1/transactions', data);

    if (!response.data.data) {
        throw new Error('Invalid response from transaction endpoint');
    }

    return response.data.data;
}

/**
 * Get the current balance for a fund
 * @param fundId - Fund ID
 * @returns Balance information
 */
export async function getBalance(fundId: string): Promise<BalanceResponse> {
    const response = await apiClient.get<APIResponse<BalanceResponse>>('/api/v1/transactions/balance', {
        params: { fund_id: fundId }
    });

    if (!response.data.data) {
        throw new Error('Invalid response from balance endpoint');
    }

    return response.data.data;
}

/**
 * Update an existing transaction
 * @param id - Transaction ID
 * @param data - Updated transaction data
 * @returns Updated transaction
 */
export async function updateTransaction(id: string, data: CreateTransactionDto): Promise<Transaction> {
    const response = await apiClient.put<APIResponse<Transaction>>(`/api/v1/transactions/${id}`, data);

    if (!response.data.data) {
        throw new Error('Invalid response from transaction endpoint');
    }

    return response.data.data;
}

/**
 * Delete a transaction
 * @param id - Transaction ID
 */
export async function deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/transactions/${id}`);
}
