import { apiClient } from './client';
import { PaginatedResponse, APIResponse } from './types';

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

export type TradeStatus = 'OPEN' | 'CLOSED' | 'REJECTED' | 'ALL';
export type TradeDirection = 'LONG' | 'SHORT';

export interface Trade {
    trade_id: string;
    symbol: string;
    strategy_name: string;
    signal_timestamp: string;
    direction: TradeDirection;
    entry_price: number;
    sl_price: number;
    tp_price: number;
    lot_size: number;
    risk_usd: number;
    status: TradeStatus;
    pnl_usd?: number;
    exit_price?: number;
    exit_timestamp?: string;
    rejection_reason?: string;
    created_at: string;
    updated_at: string;
}

export interface GetTradesParams {
    page?: number;
    per_page?: number;
    status?: TradeStatus;
    symbol?: string;
    from_date?: string;
    to_date?: string;
}

/**
 * Get real-time account summary from OANDA (via Execution Service)
 */
export async function getAccountSummary(): Promise<AccountSummary> {
    const response = await apiClient.get<AccountSummary | { data: AccountSummary }>('/api/v1/execution/account/summary');
    if ('data' in response.data) {
        return response.data.data;
    }
    return response.data as AccountSummary;
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

/**
 * Get trades with filtering and pagination
 */
export async function getTrades(params: GetTradesParams = {}): Promise<PaginatedResponse<Trade>> {
    const response = await apiClient.get<PaginatedResponse<Trade>>('/api/v1/execution/trades', { params });
    return response.data;
}

export interface ExecutionBrokerAccount {
    id: string;
    broker_name: string;
    account_id: string; // The external broker ID (e.g., "101-001-...")
}

export interface SmartOrderRequest {
    broker_account_id: string;
    symbol: string;
    direction: 'BULLISH' | 'BEARISH';
    stop_loss?: number;
    generated_by: string;
    reason?: string;
    risk_usd?: number;
}



export async function getBrokerAccounts(): Promise<ExecutionBrokerAccount[]> {
    const response = await apiClient.get<APIResponse<ExecutionBrokerAccount[]> | ExecutionBrokerAccount[]>('/api/v1/execution/accounts');
    if ('data' in response.data && Array.isArray(response.data.data)) {
        return response.data.data;
    }
    return response.data as ExecutionBrokerAccount[];
}

export async function placeSmartOrder(data: SmartOrderRequest): Promise<OrderResponse> {
    const response = await apiClient.post<OrderResponse>('/api/v1/execution/smart-orders', data);
    return response.data;
}
