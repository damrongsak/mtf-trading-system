import { DashboardStats, RecentSignal } from './types';

/**
 * Get dashboard statistics
 * Note: Currently returns mock data. Replace with real API endpoint when available.
 * @returns Dashboard statistics
 */
export async function getDashboardStats(): Promise<DashboardStats> {
    // TODO: Replace with real API call when /api/v1/dashboard endpoint is implemented
    // const response = await apiClient.get<DashboardStats>('/api/v1/dashboard/stats');
    // return response.data;

    // Mock data for now
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                total_pnl: 1250.50,
                total_trades: 47,
                winning_trades: 32,
                losing_trades: 15,
                win_rate: 68.09,
                open_positions: 2,
                avg_win: 125.30,
                avg_loss: -85.20,
            });
        }, 500); // Simulate network delay
    });
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
