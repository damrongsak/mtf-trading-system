import { apiClient } from './client';
import { DashboardStats, RecentSignal } from './types';

/**
 * Get dashboard statistics
 * Note: Currently returns mock data. Replace with real API endpoint when available.
 * @returns Dashboard statistics
 */
export async function getDashboardStats(): Promise<DashboardStats> {
    const response = await apiClient.get<DashboardStats>('/api/v1/dashboard/stats');
    return response.data;
}

export interface EquityPoint {
    date: string;
    equity: number;
    daily_pnl: number;
}

export async function getEquityCurve(days: number = 30): Promise<EquityPoint[]> {
    const response = await apiClient.get<EquityPoint[]>(`/api/v1/dashboard/equity-curve?days=${days}`);
    return response.data;
}

export interface StrategyPerformance {
    strategy_name: string;
    total_trades: number;
    total_pnl: number;
    win_rate: number;
}

export async function getStrategyPerformance(): Promise<StrategyPerformance[]> {
    const response = await apiClient.get<StrategyPerformance[]>('/api/v1/dashboard/performance');
    return response.data;
}

/**
 * Get recent trading signals
 * @param limit - Number of recent signals to fetch (default: 5)
 * @returns Array of recent signals
 */
export async function getRecentSignals(limit: number = 5): Promise<RecentSignal[]> {
    // TODO: Update to use real signal list endpoint when pagination is available
    // const response = await apiClient.get<RecentSignal[]>(`/api/v1/signals?limit=${limit}`);
    // return response.data;

    // Mock data for now
    return new Promise((resolve) => {
        setTimeout(() => {
            const mockSignals: RecentSignal[] = [
                {
                    id: '1',
                    symbol: 'XAU/USD',
                    direction: 'BULLISH' as const,
                    confidence: 85,
                    timeframe: '15m',
                    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
                    entry_price: 2045.30,
                },
                {
                    id: '2',
                    symbol: 'XAU/USD',
                    direction: 'BEARISH' as const,
                    confidence: 72,
                    timeframe: '1H',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
                    entry_price: 2048.90,
                },
                {
                    id: '3',
                    symbol: 'XAU/USD',
                    direction: 'BULLISH' as const,
                    confidence: 91,
                    timeframe: '4H',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
                    entry_price: 2042.15,
                },
                {
                    id: '4',
                    symbol: 'XAU/USD',
                    direction: 'NEUTRAL' as const,
                    confidence: 45,
                    timeframe: '15m',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
                    entry_price: 2050.00,
                },
                {
                    id: '5',
                    symbol: 'XAU/USD',
                    direction: 'BULLISH' as const,
                    confidence: 78,
                    timeframe: '1H',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
                    entry_price: 2039.75,
                },
            ];
            resolve(mockSignals.slice(0, limit));
        }, 300);
    });
}
