import { apiClient } from './client';
import { DashboardStats, RecentSignal } from './types';

/**
 * Get dashboard statistics
 * @returns Dashboard statistics
 */
export async function getDashboardStats(strategyId?: string): Promise<DashboardStats> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: Record<string, any> = {};
    if (strategyId && strategyId !== 'all') params.strategy_id = strategyId;

    const response = await apiClient.get<DashboardStats>('/api/v1/dashboard/stats', { params });
    return response.data;
}

export interface EquityPoint {
    date: string;
    equity: number;
    daily_pnl: number;
}

export async function getEquityCurve(days: number = 30, strategyId?: string): Promise<EquityPoint[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: Record<string, any> = { days };
    if (strategyId && strategyId !== 'all') params.strategy_id = strategyId;

    const response = await apiClient.get<EquityPoint[]>('/api/v1/dashboard/equity-curve', { params });
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
import { getBatchSignals, getDetectedSignals } from './signals';

/**
 * Get recent trading signals
 * @param limit - Number of recent signals to fetch (default: 5)
 * @returns Array of recent signals
 */
export async function getRecentSignals(limit: number = 5): Promise<RecentSignal[]> {
    try {
        // Fetch from both sources in parallel
        const [scannerSignals, detectedSignals] = await Promise.all([
            getBatchSignals("OANDA"),
            getDetectedSignals(limit * 2)
        ]);

        // Merge strategies (preferring detected if duplicates exist? 
        // Actually, scanner signals are ephemeral ("now"). Detected are "history". 
        // If scanner signal is "now", it might not be in DB yet if not executed/persisted by a deployment.
        // But scanner signals are "potential" signals.
        // Detected signals are FROM deployments (Scanner defaults usually don't save to DB unless we add autosave).
        // For now, simple merge.

        const allSignals = [...detectedSignals, ...scannerSignals];

        // Remove duplicates based on ID (Symbol + Timestamp)
        const uniqueSignals = Array.from(new Map(allSignals.map(item =>
            [`${item.symbol}-${item.timestamp}`, item]
        )).values());

        const validSignals = uniqueSignals
            .filter(s => s.direction !== 'NEUTRAL')
            .map(s => {
                const mapDirection = (dir: string): 'BULLISH' | 'BEARISH' | 'NEUTRAL' => {
                    if (dir === 'LONG') return 'BULLISH';
                    if (dir === 'SHORT') return 'BEARISH';
                    if (dir === 'BULLISH') return 'BULLISH';
                    if (dir === 'BEARISH') return 'BEARISH';
                    return 'NEUTRAL';
                };

                return {
                    id: `${s.symbol}-${s.timestamp}`,
                    symbol: s.symbol,
                    direction: mapDirection(s.direction),
                    confidence: s.confidence || 0.75,
                    timeframe: s.timeframe,
                    timestamp: s.timestamp,
                    entry_price: s.entry_price,
                    sl_price: s.sl_price,
                    tp_price: s.tp_price,
                    reason: s.reason,
                    broker: s.broker,
                    strategy_name: s.strategy_name,
                } as RecentSignal;
            });

        // Sort by timestamp descending
        validSignals.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        return validSignals.slice(0, limit);
    } catch (error) {
        console.error("Error fetching recent signals", error);
        return [];
    }
}
