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
    account_id: string; // The internal BrokerAccount UUID
    symbol: string;
    order_type: 'MARKET' | 'LIMIT' | 'STOP'; // Explicit type
    units: number; // positive for long, negative for short
    price?: number; // For Limit/Stop inputs
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
    status: string;
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
    account_id?: string;
}

/**
 * Get real-time account summary from OANDA (via Execution Service)
 */
export async function getAccountSummary(accountId?: string): Promise<AccountSummary> {
    const params = accountId ? { account_id: accountId } : {};
    const response = await apiClient.get<APIResponse<AccountSummary>>('/api/v1/execution/account/summary', { params });
    return response.data.data!;
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

/**
 * Get open positions directly from broker
 */
export async function getOpenPositions(accountId: string): Promise<Trade[]> {
    const response = await apiClient.post<{ status: string, data: Trade[] }>('/api/v1/execution/trades/open', { broker_account_id: accountId });
    return response.data.data;
}

export interface ExecutionBrokerAccount {
    id: string;
    broker_name: string;
    account_id: string; // The external broker ID (e.g., "101-001-...")
    environment: string;
}

export interface SmartOrderRequest {
    broker_account_id: string;
    symbol: string;
    direction: 'BULLISH' | 'BEARISH';
    stop_loss?: number;
    take_profit?: number;
    entry_price?: number; // For Limit/Stop orders
    time_in_force?: 'GTC' | 'GTD' | 'GFD' | 'FOK' | 'IOC';
    slippage_tolerance?: number; // e.g. 0.0001 (price dist) or percent
    generated_by: string;
    reason?: string;
    risk_usd?: number;
    // Minimax / AI Inputs
    confidence?: number;
    atr_multiplier?: number;
    pain_threshold?: number;
}



export async function getBrokerAccounts(): Promise<ExecutionBrokerAccount[]> {
    const response = await apiClient.get<APIResponse<ExecutionBrokerAccount[]>>('/api/v1/execution/accounts');
    return response.data.data || [];
}

/**
 * Get pending orders for an account
 */
export async function getPendingOrders(accountId: string): Promise<OrderResponse[]> {
    const response = await apiClient.get<APIResponse<OrderResponse[]>>('/api/v1/execution/orders', {
        params: { broker_account_id: accountId }
    });
    return response.data.data || [];
}


export async function placeSmartOrder(data: SmartOrderRequest): Promise<OrderResponse> {
    const response = await apiClient.post<OrderResponse>('/api/v1/execution/smart-orders', data);
    return response.data;
}

/**
 * Close all open trades for an account (Panic Button)
 */
export async function closeAllTrades(accountId: string, symbol?: string): Promise<{ count: number, errors: string[] }> {
    const response = await apiClient.post<{ count: number, errors: string[] }>('/api/v1/execution/trades/close-all', {
        broker_account_id: accountId,
        symbol
    });
    return response.data;
}

/**
 * Cancel a specific order
 */
export async function cancelOrder(orderId: string): Promise<void> {
    await apiClient.delete(`/api/v1/execution/orders/${orderId}`);
}

/**
 * Cancel all pending orders
 */
export async function cancelAllOrders(accountId: string, symbol?: string): Promise<{ cancelled: number, errors: string[] }> {
    // Note: Axios delete with body is not standard, using query params
    const response = await apiClient.delete<{ cancelled: number, errors: string[] }>('/api/v1/execution/orders', {
        params: { broker_account_id: accountId, symbol }
    });
    return response.data;
}
