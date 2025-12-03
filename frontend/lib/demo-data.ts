/**
 * Mock data for guest home page demo/preview
 */

export interface DemoSignal {
    id: string;
    symbol: string;
    direction: 'BULLISH' | 'BEARISH';
    confidence: number;
    timeframe: string;
    timestamp: string;
    setup: string;
}

export const demoSignals: DemoSignal[] = [
    {
        id: '1',
        symbol: 'XAU/USD',
        direction: 'BULLISH',
        confidence: 87,
        timeframe: '15m',
        timestamp: '2 hours ago',
        setup: 'Fibo 61.8% + Order Block',
    },
    {
        id: '2',
        symbol: 'XAU/USD',
        direction: 'BEARISH',
        confidence: 72,
        timeframe: '1h',
        timestamp: '5 hours ago',
        setup: 'Fibo 50% + SMC Zone',
    },
    {
        id: '3',
        symbol: 'XAU/USD',
        direction: 'BULLISH',
        confidence: 91,
        timeframe: '4h',
        timestamp: '8 hours ago',
        setup: 'EMA200 Bounce + OB',
    },
];

export interface StatMetric {
    label: string;
    value: string;
    trend?: 'up' | 'down';
}

export const demoStats: StatMetric[] = [
    { label: 'Win Rate', value: '68.5%', trend: 'up' },
    { label: 'Avg R:R Ratio', value: '2.8:1', trend: 'up' },
    { label: 'Trades This Month', value: '142' },
    { label: 'Active Signals', value: '12' },
];
