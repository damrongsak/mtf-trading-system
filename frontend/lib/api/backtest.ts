import { apiClient } from './client';
import { ApiError } from './types';

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  strategy_params: Record<string, any>;
  start_date: string; // ISO Date string
  end_date: string;   // ISO Date string
  initial_capital?: number;
  fees?: number;
  slippage?: number;
  strategy_id?: string;
  fund_id?: string;
}

export interface TradeResult {
  entry_time: string;
  exit_time: string;
  direction: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_percent: number;
}

export interface KeyMetrics {
  total_return: number;
  total_return_percent: number;
  max_drawdown: number;
  max_drawdown_percent: number;
  win_rate: number;
  benchmark_return?: number;
  sharpe_ratio?: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

export interface EquityPoint {
    timestamp: string;
    value: number;
}

export interface BacktestResponse {
  id: string;
  status: string;
  metrics?: KeyMetrics;
  trades: TradeResult[];
  equity_curve: EquityPoint[];
  best_params?: Record<string, any>;
}

export async function runBacktest(payload: BacktestRequest): Promise<BacktestResponse> {
  const response = await apiClient.post<BacktestResponse>('/api/v1/backtest/run', payload);
  return response.data;
}
