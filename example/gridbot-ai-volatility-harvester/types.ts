
export enum OrderType {
  BUY = 'BUY',
  SELL = 'SELL',
}

export enum TrendMode {
  SIDEWAYS = 'SIDEWAYS',
  UPTREND = 'UPTREND',
  DOWNTREND = 'DOWNTREND',
}

export enum GridSpacingType {
  ARITHMETIC = 'ARITHMETIC',
  GEOMETRIC = 'GEOMETRIC',
}

export enum GridSizingType {
  FIXED = 'FIXED',
  MARTINGALE = 'MARTINGALE',
  ANTI_MARTINGALE = 'ANTI_MARTINGALE',
}

export enum BotStatus {
  RUNNING = 'RUNNING',
  HALTED = 'HALTED',
  LIQUIDATED = 'LIQUIDATED',
  DEFENSE = 'DEFENSE', // DD Guard Active
}

export enum MarketAnomaly {
  NONE = 'NONE',
  PUMP_DUMP = 'PUMP_DUMP',
  FLASH_CRASH = 'FLASH_CRASH',
  HIGH_VOL_REGIME = 'HIGH_VOL_REGIME',
  MEAN_REVERSION = 'MEAN_REVERSION',
}

export enum IndicatorType {
  NONE = 'NONE',
  BOLLINGER = 'BOLLINGER',
  DONCHIAN = 'DONCHIAN',
  ATR_BANDS = 'ATR_BANDS',
}

export interface GridLevel {
  id: string;
  price: number;
  type: OrderType;
  status: 'PENDING' | 'FILLED';
}

export interface Trade {
  id: string;
  timestamp: number;
  price: number;
  type: OrderType;
  amount: number;
  pnl?: number; // Realized PnL for sells
  fee?: number; // Transaction cost
}

export interface Position {
  price: number;
  amount: number;
  timestamp: number;
}

export interface BotConfig {
  initialCapital: number;
  assetSymbol: string; // 'BTC', 'XAU', 'EUR', etc.
  initialPrice: number; // Starting price of the asset
  gridTop: number;
  gridBottom: number;
  gridCount: number;
  orderSize: number; // Fixed volume units per grid
  
  // Execution Model (Realism)
  transactionFee: number; // Percentage (e.g., 0.1 for 0.1%)
  marketSpread: number; // Percentage (e.g., 0.05 for spread width)

  // Advanced Grid Design
  spacingType: GridSpacingType;
  sizingType: GridSizingType;

  // Triggers
  maxBuyPrice: number;
  minSellPrice: number;
  
  // Risk Management
  riskStopLoss: number; // % Equity Drop
  riskDrawdownGuard: number; // % Drawdown to stop new buys
  
  // Simulation
  trendMode: TrendMode;
  volatility: number; // 0.0 to 1.0 representation
  anomaly: MarketAnomaly; // Market Anomaly Type
  simSpeed: number; // ms
  
  // Technicals
  activeIndicator: IndicatorType;
}

export interface BotStats {
  cash: number;
  holdings: number;
  totalEquity: number;
  initialCapital: number;
  totalPnL: number;
  roi: number;
  maxDrawdown: number;
  totalBuys: number;
  totalSells: number;
  gridProfit: number; // Realized from Grid
  floatingPnL: number; // Unrealized on holdings
  portfolioVolatility: number; // StdDev of returns (simplified)
  status: BotStatus;
}

export interface PricePoint {
  time: string; 
  price: number;
  equity: number;
  timestamp: number;
  upperBand?: number; // For Indicators
  lowerBand?: number; // For Indicators
}

export interface SimulationResult {
  runId: number;
  finalEquity: number;
  pnl: number;
  roi: number;
  maxDrawdown: number;
  gridProfit: number;
  tradesCount: number;
  isLiquidation: boolean;
  isRuined: boolean; // Equity < 50%
}

export interface MonteCarloStats {
  iterations: number;
  avgRoi: number;
  medianRoi: number;
  bestCase: number;
  worstCase: number;
  avgMaxDrawdown: number;
  var95: number; // Value at Risk (95% confidence)
  winRate: number; // % of profitable runs
  riskOfRuin: number; // % Probability of ruin
  results: SimulationResult[];
}

// AI Analyst Types
export interface ScenarioSuggestion {
  name: string;
  description: string;
  configOverrides: Partial<BotConfig>;
}

export interface AIAnalysisResult {
  healthScore: number; // 0-100
  explanation: string;
  suggestions: ScenarioSuggestion[];
}
