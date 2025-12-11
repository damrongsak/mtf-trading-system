import { apiClient } from './client';

export interface AccountSummary {
    balance: string;
    NAV: string;
    marginAvailable: string;
    openTradeCount: number;
    openPositionCount: number;
}

export interface OrderRequest {
    symbol: string;
    units: number; // positive for long, negative for short
    sl_price?: number;
    tp_price?: number;
    trade_id?: string;
}

export interface OrderResponse {
    id: string;
    instrument: string;
    units: string;
    price: string;
    time: string;
}

/**
 * Get real-time account summary from OANDA (via Execution Service)
 */
export async function getAccountSummary(): Promise<AccountSummary> {
    const response = await apiClient.get<AccountSummary>('/api/v1/execution/account/summary');
    return response.data;
}

/**
 * Place a market order
 */
export async function placeOrder(data: OrderRequest): Promise<OrderResponse> {
    const response = await apiClient.post<OrderResponse>('/api/v1/execution/orders', data);
    return response.data;
}

export interface CloseTradeResponse {
    status: string;
    trade_id: string;
    pnl: number;
    exit_price: number;
}

/**
 * Close a trade manually
 */
export async function closeTrade(tradeId: string, exitPrice: number): Promise<CloseTradeResponse> {
    const response = await apiClient.post<CloseTradeResponse>(`/api/v1/execution/trades/${tradeId}/close`, { exit_price: exitPrice });
    return response.data;
}
