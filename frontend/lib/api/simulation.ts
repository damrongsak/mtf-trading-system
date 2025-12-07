import { SimulationConfig, SimulationResult, APIResponse, ResponseStatus } from './types';

const MOCK_DELAY = 1500; // Simulate network latency

/**
 * Mock function to run a GRID simulation
 */
export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
    return new Promise((resolve) => {
        setTimeout(() => {
            const result: SimulationResult = {
                id: crypto.randomUUID(),
                config,
                status: 'COMPLETED',
                created_at: new Date().toISOString(),
                metrics: {
                    total_pnl: generateRandomPnL(config),
                    win_rate: 65 + Math.random() * 10,
                    max_drawdown: 12 + Math.random() * 8,
                    sharpe_ratio: 1.2 + Math.random() * 0.8,
                    profit_factor: 1.5 + Math.random() * 0.5,
                },
                equity_curve: generateMockEquityCurve(100),
            };
            resolve(result);
        }, MOCK_DELAY);
    });
}

function generateRandomPnL(config: SimulationConfig): number {
    const basePnL = 5000;
    const volatilityFactor = config.regime.volatility / 5;
    const noiseImpact = config.regime.noise === 'FAT_TAIL' ? (Math.random() > 0.8 ? -2000 : 500) : 0;
    return basePnL * volatilityFactor + noiseImpact;
}

function generateMockEquityCurve(points: number): { timestamp: string; value: number }[] {
    let equity = 10000;
    const curve = [];
    const now = new Date();

    for (let i = 0; i < points; i++) {
        const change = (Math.random() - 0.45) * 100; // Slight upward bias
        equity += change;
        const date = new Date(now.getTime() - (points - i) * 3600000); // Hourly points
        curve.push({
            timestamp: date.toISOString(),
            value: equity
        });
    }
    return curve;
}
