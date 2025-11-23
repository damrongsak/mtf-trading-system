
import { BotConfig, GridLevel, OrderType, SimulationResult, TrendMode, MonteCarloStats } from '../types';

// Pure logic version of the Grid Bot for fast batch processing
export const runMonteCarlo = (config: BotConfig, iterations: number = 100, ticksPerRun: number = 1000): MonteCarloStats => {
  const results: SimulationResult[] = [];

  for (let i = 0; i < iterations; i++) {
    results.push(runSingleSim(i, config, ticksPerRun));
  }

  // Calculate Aggregated Stats
  const rois = results.map(r => r.roi).sort((a, b) => a - b);
  const totalRoi = rois.reduce((a, b) => a + b, 0);
  const avgRoi = totalRoi / iterations;
  const medianRoi = rois[Math.floor(iterations / 2)];
  
  const totalDD = results.reduce((a, b) => a + b.maxDrawdown, 0);
  const avgMaxDrawdown = totalDD / iterations;

  // VaR 95% (The 5th percentile worst outcome)
  const varIndex = Math.floor(iterations * 0.05);
  const var95 = rois[varIndex]; // The ROI at the bottom 5%

  const winRate = (results.filter(r => r.pnl > 0).length / iterations) * 100;
  
  // Risk of Ruin: % of runs where equity drops below 50% of capital (proxy for ruin)
  const ruinedRuns = results.filter(r => r.isRuined).length;
  const riskOfRuin = (ruinedRuns / iterations) * 100;

  return {
    iterations,
    avgRoi,
    medianRoi,
    bestCase: rois[iterations - 1],
    worstCase: rois[0],
    avgMaxDrawdown,
    var95,
    winRate,
    riskOfRuin,
    results
  };
};

const runSingleSim = (runId: number, config: BotConfig, ticks: number): SimulationResult => {
  let cash = config.initialCapital;
  let holdings = 0;
  let currentPrice = config.initialPrice;
  let gridProfit = 0;
  let tradesCount = 0;
  let peakEquity = config.initialCapital;
  let maxDrawdown = 0;
  let isRuined = false;

  // Initialize Grid
  const step = (config.gridTop - config.gridBottom) / config.gridCount;
  let gridLevels: GridLevel[] = [];
  for (let i = 0; i <= config.gridCount; i++) {
    const price = config.gridBottom + (i * step);
    const isBuy = price < currentPrice;
    gridLevels.push({
      id: `sim-${runId}-${i}`,
      price,
      type: isBuy ? OrderType.BUY : OrderType.SELL,
      status: 'PENDING'
    });
  }

  const feeRate = config.transactionFee / 100;
  const spreadFactor = config.marketSpread / 100;

  // Simulation Loop
  for (let t = 0; t < ticks; t++) {
    // Price Movement (GBM-like)
    let drift = 0;
    if (config.trendMode === TrendMode.UPTREND) drift = 0.0002;
    if (config.trendMode === TrendMode.DOWNTREND) drift = -0.0002;

    const volMagnitude = 0.001 + (config.volatility * 0.02);
    const shock = (Math.random() - 0.5) * 2 * volMagnitude;
    
    currentPrice = Math.max(0.01, currentPrice * (1 + drift + shock));
    const askPrice = currentPrice * (1 + spreadFactor / 2);
    const bidPrice = currentPrice * (1 - spreadFactor / 2);

    // Grid Logic
    let levelsChanged = false;
    for (let l = 0; l < gridLevels.length; l++) {
        const level = gridLevels[l];
        if (level.status !== 'PENDING') continue;

        if (level.type === OrderType.BUY && askPrice <= level.price) {
            if (currentPrice > config.maxBuyPrice) continue;
            const cost = level.price * config.orderSize;
            const fee = cost * feeRate;

            if (cash >= cost + fee) {
                cash -= (cost + fee);
                holdings += config.orderSize;
                tradesCount++;
                
                gridLevels[l] = {
                    ...level,
                    price: level.price + step,
                    type: OrderType.SELL,
                    status: 'PENDING'
                };
                levelsChanged = true;
            }
        } else if (level.type === OrderType.SELL && bidPrice >= level.price) {
            if (currentPrice < config.minSellPrice) continue;
            if (holdings >= config.orderSize) {
                const revenue = level.price * config.orderSize;
                const fee = revenue * feeRate;
                
                cash += (revenue - fee);
                holdings -= config.orderSize;
                
                const grossProfit = config.orderSize * step;
                gridProfit += (grossProfit - (2 * fee)); // Approx net
                tradesCount++;

                gridLevels[l] = {
                    ...level,
                    price: level.price - step,
                    type: OrderType.BUY,
                    status: 'PENDING'
                };
                levelsChanged = true;
            }
        }
    }

    // Equity & Drawdown Calc
    const equity = cash + (holdings * currentPrice);
    if (equity > peakEquity) peakEquity = equity;
    const dd = peakEquity > 0 ? ((peakEquity - equity) / peakEquity) * 100 : 0;
    if (dd > maxDrawdown) maxDrawdown = dd;
    
    if (equity < config.initialCapital * 0.5) isRuined = true;
  }

  const finalEquity = cash + (holdings * currentPrice);
  const pnl = finalEquity - config.initialCapital;
  const roi = (pnl / config.initialCapital) * 100;

  return {
    runId,
    finalEquity,
    pnl,
    roi,
    maxDrawdown,
    gridProfit,
    tradesCount,
    isLiquidation: finalEquity <= 0,
    isRuined
  };
};
