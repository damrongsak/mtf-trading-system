import { apiClient } from './client';
import { DashboardStats, RecentSignal, Signal, APIResponse } from './types';

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
export async function getRecentSignals(limit: number = 5, symbols?: string[]): Promise<RecentSignal[]> {
    const defaultWatchlist = ['XAU/USD', 'EUR/USD', 'GBP/USD', 'BTC/USD', 'USD/JPY'];
    const watchlist = symbols && symbols.length > 0 ? symbols : defaultWatchlist;

    try {
        const promises = watchlist.map(async (symbol) => {
            try {
                // We use the signals API we just created
                // Importing here to avoid circular dependency if signals imports dashboard
                // But signals.ts is independent.
                // However, we need to import `getLatestSignal` from `./signals`.
                // If dashboard.ts is used by signals.ts, that's an issue. 
                // signals.ts depends on client.ts and types.ts. dashboard.ts depends on client.ts and types.ts. Safe.

                // Since we can't easily add import top-level in this replace block given the file structure
                // effectively, I will assume I can modify the imports in a separate step or I'll implement the call here directly via apiClient
                // to avoid modifying imports at the top of the file which might be messy with line numbers.
                // Actually, I should use `apiClient` directly here to match existing pattern.

                // Call /api/v1/signal/latest/{symbol}
                const response = await apiClient.get<APIResponse<Signal>>(`/api/v1/signal/latest/${encodeURIComponent(symbol)}`);
                const signal = response.data.data;

                if (!signal) return null;

                const mapDirection = (dir: string): 'BULLISH' | 'BEARISH' | 'NEUTRAL' => {
                    if (dir === 'LONG') return 'BULLISH';
                    if (dir === 'SHORT') return 'BEARISH';
                    if (dir === 'BULLISH') return 'BULLISH';
                    if (dir === 'BEARISH') return 'BEARISH';
                    return 'NEUTRAL';
                };

                return {
                    id: `${signal.symbol}-${signal.timestamp}`,
                    symbol: signal.symbol,
                    direction: mapDirection(signal.direction),
                    confidence: signal.confidence || 0.75, // Default confidence if missing
                    timeframe: signal.timeframe,
                    timestamp: signal.timestamp,
                    entry_price: signal.entry_price,
                    reason: signal.reason, // Pass reason through
                } as RecentSignal;
            } catch (e) {
                console.warn(`Failed to fetch signal for ${symbol}`, e);
                return null;
            }
        });

        const results = await Promise.all(promises);
        const validSignals = results.filter((s): s is RecentSignal => s !== null);

        // Sort by timestamp if available or just return
        // Ideally newest first.
        validSignals.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        return validSignals.slice(0, limit);
    } catch (error) {
        console.error("Error fetching recent signals", error);
        return [];
    }
}
