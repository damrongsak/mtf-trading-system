
import { useState, useEffect, useRef, useCallback } from 'react';
import { BotConfig, BotStats, GridLevel, OrderType, PricePoint, Trade, TrendMode, Position, GridSpacingType, GridSizingType, BotStatus, MarketAnomaly, IndicatorType } from '../types';

const DEFAULT_CONFIG: BotConfig = {
  initialCapital: 10000,
  assetSymbol: 'BTC',
  initialPrice: 95000,
  gridTop: 105000,
  gridBottom: 85000,
  gridCount: 30,
  orderSize: 0.1, 
  spacingType: GridSpacingType.ARITHMETIC,
  sizingType: GridSizingType.FIXED,
  transactionFee: 0.1, // 0.1%
  marketSpread: 0.05, // 0.05%
  maxBuyPrice: 105000,
  minSellPrice: 85000,
  riskStopLoss: 20, // 20% max loss
  riskDrawdownGuard: 10, // 10% DD guard
  trendMode: TrendMode.SIDEWAYS,
  volatility: 0.45,
  anomaly: MarketAnomaly.NONE,
  simSpeed: 50,
  activeIndicator: IndicatorType.NONE,
};

export const useGridBot = () => {
  const [config, setConfig] = useState<BotConfig>(DEFAULT_CONFIG);
  const [isRunning, setIsRunning] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(DEFAULT_CONFIG.initialPrice);
  const [botStatus, setBotStatus] = useState<BotStatus>(BotStatus.RUNNING);
  
  // Simulation State
  const [gridLevels, setGridLevels] = useState<GridLevel[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [activePositions, setActivePositions] = useState<Position[]>([]);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  
  // Refs for simulation loop
  const stateRef = useRef({
    cash: DEFAULT_CONFIG.initialCapital,
    holdings: 0,
    currentPrice: DEFAULT_CONFIG.initialPrice,
    gridLevels: [] as GridLevel[],
    trades: [] as Trade[],
    positions: [] as Position[],
    peakEquity: DEFAULT_CONFIG.initialCapital,
    maxDrawdown: 0,
    gridProfit: 0,
    equityHistory: [] as number[],
    recentPrices: [] as number[], // For Indicator Calc
    status: BotStatus.RUNNING,
    tickCount: 0, 
  });

  const configRef = useRef(config);
  useEffect(() => {
    configRef.current = config;
  }, [config]);

  // Helper to calculate stats
  const getStats = (): BotStats => {
    const currentEquity = stateRef.current.cash + (stateRef.current.holdings * stateRef.current.currentPrice);
    const totalPnL = currentEquity - config.initialCapital;
    const roi = (totalPnL / config.initialCapital) * 100;
    
    const floatingPnL = currentEquity - (config.initialCapital + stateRef.current.gridProfit);

    // Update Peak Equity for Drawdown calc
    if (currentEquity > stateRef.current.peakEquity) {
      stateRef.current.peakEquity = currentEquity;
    }
    
    const drawdown = stateRef.current.peakEquity > 0 
      ? ((stateRef.current.peakEquity - currentEquity) / stateRef.current.peakEquity) * 100 
      : 0;

    if (drawdown > stateRef.current.maxDrawdown) {
      stateRef.current.maxDrawdown = drawdown;
    }

    const buys = stateRef.current.trades.filter(t => t.type === OrderType.BUY).length;
    const sells = stateRef.current.trades.filter(t => t.type === OrderType.SELL).length;

    let vol = 0;
    const len = stateRef.current.equityHistory.length;
    if (len > 2) {
        const slice = stateRef.current.equityHistory.slice(-20);
        const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
        const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / slice.length;
        vol = Math.sqrt(variance) / mean * 100;
    }

    return {
      cash: stateRef.current.cash,
      holdings: stateRef.current.holdings,
      totalEquity: currentEquity,
      initialCapital: config.initialCapital,
      totalPnL,
      roi,
      maxDrawdown: stateRef.current.maxDrawdown,
      totalBuys: buys,
      totalSells: sells,
      gridProfit: stateRef.current.gridProfit,
      floatingPnL,
      portfolioVolatility: vol,
      status: stateRef.current.status
    };
  };

  const initializeGrid = useCallback(() => {
    const effectivePrice = stateRef.current.currentPrice;
    
    const newLevels: GridLevel[] = [];
    
    // Grid Generation Strategy
    if (config.spacingType === GridSpacingType.ARITHMETIC) {
        const step = (config.gridTop - config.gridBottom) / config.gridCount;
        for (let i = 0; i <= config.gridCount; i++) {
          const price = config.gridBottom + (i * step);
          const isBuy = price < effectivePrice;
          newLevels.push({
            id: `level-${i}`,
            price,
            type: isBuy ? OrderType.BUY : OrderType.SELL,
            status: 'PENDING'
          });
        }
    } else {
        // GEOMETRIC (Logarithmic)
        const ratio = Math.pow(config.gridTop / config.gridBottom, 1 / config.gridCount);
        for (let i = 0; i <= config.gridCount; i++) {
            const price = config.gridBottom * Math.pow(ratio, i);
            const isBuy = price < effectivePrice;
            newLevels.push({
                id: `level-${i}`,
                price,
                type: isBuy ? OrderType.BUY : OrderType.SELL,
                status: 'PENDING'
            });
        }
    }
    
    setGridLevels(newLevels);
    stateRef.current.gridLevels = newLevels;
    stateRef.current.trades = [];
    stateRef.current.positions = [];
    stateRef.current.gridProfit = 0;
    stateRef.current.maxDrawdown = 0;
    stateRef.current.peakEquity = config.initialCapital;
    stateRef.current.cash = config.initialCapital;
    stateRef.current.holdings = 0;
    stateRef.current.equityHistory = [config.initialCapital];
    stateRef.current.recentPrices = [effectivePrice];
    stateRef.current.status = BotStatus.RUNNING;
    stateRef.current.tickCount = 0;
    
    setTrades([]);
    setActivePositions([]);
    setBotStatus(BotStatus.RUNNING);
    
    const startPoint: PricePoint = { 
      time: new Date().toLocaleTimeString(), 
      price: effectivePrice, 
      equity: config.initialCapital,
      timestamp: Date.now() 
    };
    setPriceHistory([startPoint]);
    setCash(config.initialCapital);
    setHoldings(0);
  }, [config]);

  const reset = () => {
    setIsRunning(false);
    const startPrice = config.initialPrice;
    setCurrentPrice(startPrice);
    stateRef.current.currentPrice = startPrice;
    initializeGrid();
  };
  
  const saveConfig = () => {
      localStorage.setItem('gridBotConfig', JSON.stringify(config));
      alert('Strategy Saved!');
  };

  const loadConfig = () => {
      const saved = localStorage.getItem('gridBotConfig');
      if (saved) {
          const parsed = JSON.parse(saved);
          setConfig(parsed);
          alert('Strategy Loaded!');
      } else {
          alert('No saved strategy found.');
      }
  };

  // Instant Shock (Flash Crash Trigger)
  const triggerShock = () => {
      const shockPrice = stateRef.current.currentPrice * 0.85; // -15% instant
      stateRef.current.currentPrice = shockPrice;
      setCurrentPrice(shockPrice);
  };

  useEffect(() => {
    reset();
  }, [config.assetSymbol]);
  
  const [cash, setCash] = useState(DEFAULT_CONFIG.initialCapital);
  const [holdings, setHoldings] = useState(0);

  // Simulation Tick
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    if (isRunning) {
      interval = setInterval(() => {
        const cfg = configRef.current;
        const state = stateRef.current;
        const currentP = state.currentPrice;

        // CHECK RISK PROTOCOLS
        const currentEquity = state.cash + (state.holdings * currentP);
        
        if (currentEquity <= 0) {
            state.status = BotStatus.LIQUIDATED;
            setBotStatus(BotStatus.LIQUIDATED);
            setIsRunning(false);
            return;
        }

        const totalLossPct = ((cfg.initialCapital - currentEquity) / cfg.initialCapital) * 100;
        if (totalLossPct >= cfg.riskStopLoss && state.status !== BotStatus.HALTED) {
            state.status = BotStatus.HALTED;
            setBotStatus(BotStatus.HALTED);
            setIsRunning(false); 
            return;
        }

        const currentDD = ((state.peakEquity - currentEquity) / state.peakEquity) * 100;
        const isDefenseMode = currentDD >= cfg.riskDrawdownGuard;
        
        if (isDefenseMode && state.status !== BotStatus.DEFENSE) {
             state.status = BotStatus.DEFENSE;
             setBotStatus(BotStatus.DEFENSE);
        } else if (!isDefenseMode && state.status === BotStatus.DEFENSE) {
             state.status = BotStatus.RUNNING;
             setBotStatus(BotStatus.RUNNING);
        }

        // --- MARKET PHYSICS ENGINE ---
        state.tickCount++;
        let drift = 0;
        let volatility = cfg.volatility;
        let shock = 0;

        if (cfg.trendMode === TrendMode.UPTREND) drift = 0.002;
        if (cfg.trendMode === TrendMode.DOWNTREND) drift = -0.002;

        switch (cfg.anomaly) {
            case MarketAnomaly.PUMP_DUMP:
                const cycle = state.tickCount % 100;
                if (cycle < 60) drift += 0.005;
                else if (cycle < 80) drift -= 0.015;
                volatility *= 2;
                break;
            case MarketAnomaly.FLASH_CRASH:
                if (Math.random() < 0.02) shock = -0.08;
                else if (Math.random() < 0.05) shock = 0.03;
                volatility *= 1.5;
                break;
            case MarketAnomaly.HIGH_VOL_REGIME:
                volatility *= 3.0;
                break;
            case MarketAnomaly.MEAN_REVERSION:
                const diff = (cfg.initialPrice - currentP) / cfg.initialPrice;
                drift += diff * 0.1;
                volatility *= 0.5;
                break;
            default:
                const volMagnitude = 0.001 + (volatility * 0.03); 
                shock = (Math.random() - 0.5) * 2 * volMagnitude;
                break;
        }

        if (cfg.anomaly !== MarketAnomaly.NONE && shock === 0) {
             const volMagnitude = 0.001 + (volatility * 0.03); 
             shock = (Math.random() - 0.5) * 2 * volMagnitude;
        }

        const change = 1 + drift + shock;
        const newPrice = Math.max(0.0001, currentP * change);
        
        // --- SPREAD & EXECUTION SIMULATION ---
        const spreadFactor = cfg.marketSpread / 100; // e.g. 0.05% -> 0.0005
        const askPrice = newPrice * (1 + spreadFactor / 2); // Buys fill higher
        const bidPrice = newPrice * (1 - spreadFactor / 2); // Sells fill lower
        
        stateRef.current.currentPrice = newPrice;
        setCurrentPrice(newPrice);

        // Update Recent Prices for Indicator Calculation
        state.recentPrices.push(newPrice);
        if (state.recentPrices.length > 20) state.recentPrices.shift(); // Keep last 20

        // --- INDICATOR CALCULATION ---
        let upperBand, lowerBand;
        const lookback = state.recentPrices.length;

        if (cfg.activeIndicator !== IndicatorType.NONE && lookback >= 2) {
             const sum = state.recentPrices.reduce((a,b) => a+b, 0);
             const mean = sum / lookback;

             if (cfg.activeIndicator === IndicatorType.BOLLINGER) {
                 const variance = state.recentPrices.reduce((a,b) => a + Math.pow(b - mean, 2), 0) / lookback;
                 const stdDev = Math.sqrt(variance);
                 upperBand = mean + (2 * stdDev);
                 lowerBand = mean - (2 * stdDev);
             } else if (cfg.activeIndicator === IndicatorType.DONCHIAN) {
                 upperBand = Math.max(...state.recentPrices);
                 lowerBand = Math.min(...state.recentPrices);
             } else if (cfg.activeIndicator === IndicatorType.ATR_BANDS) {
                 const rangeSum = state.recentPrices.reduce((acc, val, i, arr) => {
                     if (i === 0) return 0;
                     return acc + Math.abs(val - arr[i-1]);
                 }, 0);
                 const atr = rangeSum / lookback;
                 upperBand = mean + (2 * atr);
                 lowerBand = mean - (2 * atr);
             }
        }

        // --- GRID ORDER MATCHING ---
        const activeLevels = [...state.gridLevels];
        let levelsChanged = false;
        let newTrade: Trade | null = null;
        
        const getDynamicSize = (baseSize: number, price: number, initialPrice: number, type: GridSizingType) => {
             if (type === GridSizingType.FIXED) return baseSize;
             const depthPct = (initialPrice - price) / initialPrice; 
             if (type === GridSizingType.MARTINGALE) {
                 if (depthPct > 0) return baseSize * (1 + (depthPct * 5)); 
             }
             if (type === GridSizingType.ANTI_MARTINGALE) {
                 if (depthPct > 0) return Math.max(baseSize * 0.1, baseSize * (1 - (depthPct * 5)));
             }
             return baseSize;
        };

        const activeOrderSize = getDynamicSize(cfg.orderSize, newPrice, cfg.initialPrice, cfg.sizingType);
        const feeRate = cfg.transactionFee / 100; // e.g. 0.1% -> 0.001

        const updatedLevels = activeLevels.map(level => {
           if (level.status === 'PENDING') {
             // BUY Logic (Check Ask Price)
             if (level.type === OrderType.BUY && askPrice <= level.price) {
                if (state.status === BotStatus.DEFENSE) return level; 
                if (newPrice > cfg.maxBuyPrice) return level; 

                const cost = level.price * activeOrderSize;
                const fee = cost * feeRate;

                if (state.cash >= cost + fee) {
                   state.cash -= (cost + fee);
                   state.holdings += activeOrderSize;
                   
                   newTrade = {
                     id: Math.random().toString(36).substr(2, 9),
                     timestamp: Date.now(),
                     price: level.price, // Filled at Limit
                     type: OrderType.BUY,
                     amount: activeOrderSize,
                     fee: fee
                   };

                   state.positions.push({
                       price: level.price,
                       amount: activeOrderSize,
                       timestamp: Date.now()
                   });
                   
                   levelsChanged = true;
                   const defaultStep = (cfg.gridTop - cfg.gridBottom) / cfg.gridCount;
                   return {
                     ...level,
                     price: level.price + defaultStep, 
                     type: OrderType.SELL,
                     status: 'PENDING'
                   } as GridLevel;
                }
             } 
             // SELL Logic (Check Bid Price)
             else if (level.type === OrderType.SELL && bidPrice >= level.price) {
                if (newPrice < cfg.minSellPrice) return level; 
                if (state.holdings >= activeOrderSize) { 
                  const revenue = activeOrderSize * level.price;
                  const fee = revenue * feeRate;
                  
                  state.cash += (revenue - fee);
                  state.holdings -= activeOrderSize;
                  
                  // Profit calculation (Simple LIFO/FIFO approximation for grid)
                  const defaultStep = (cfg.gridTop - cfg.gridBottom) / cfg.gridCount;
                  const grossProfit = activeOrderSize * defaultStep; 
                  const netProfit = grossProfit - (2 * fee); // Estimate fee for round trip
                  
                  state.gridProfit += netProfit;
                  state.positions.shift(); 

                  newTrade = {
                    id: Math.random().toString(36).substr(2, 9),
                    timestamp: Date.now(),
                    price: level.price,
                    type: OrderType.SELL,
                    amount: activeOrderSize,
                    pnl: netProfit,
                    fee: fee
                  };
                  
                  levelsChanged = true;
                  return {
                    ...level,
                    price: level.price - defaultStep,
                    type: OrderType.BUY,
                    status: 'PENDING'
                  } as GridLevel;
                }
             }
           }
           return level;
        });

        if (levelsChanged) {
           state.gridLevels = updatedLevels;
           setGridLevels(updatedLevels);
           setCash(state.cash);
           setHoldings(state.holdings);
           setActivePositions([...state.positions]);
        }

        if (newTrade) {
          const updatedTrades = [newTrade, ...state.trades].slice(0, 500);
          state.trades = updatedTrades;
          setTrades(updatedTrades);
        }

        // History Updates
        state.equityHistory.push(currentEquity);
        if (state.equityHistory.length > 1000) state.equityHistory.shift();

        const newPoint: PricePoint = {
          time: new Date().toLocaleTimeString(),
          price: newPrice,
          equity: currentEquity,
          timestamp: Date.now(),
          upperBand,
          lowerBand
        };
        
        setPriceHistory(prev => {
          const updated = [...prev, newPoint];
          return updated.length > 1000 ? updated.slice(updated.length - 1000) : updated;
        });
      }, configRef.current.simSpeed);
    }

    return () => clearInterval(interval);
  }, [isRunning]);

  return {
    config,
    setConfig,
    isRunning,
    setIsRunning,
    currentPrice,
    gridLevels,
    trades,
    activePositions,
    priceHistory,
    stats: getStats(),
    reset,
    saveConfig,
    loadConfig,
    triggerShock,
    botStatus 
  };
};
