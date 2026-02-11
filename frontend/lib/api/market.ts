import { apiClient } from './client';
import { APIResponse } from './types';

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  // Indicators might be added here dynamically or handled separately
  [key: string]: string | number;
}

export interface FetchCandlesParams {
  symbol: string;
  timeframe: string;
  from?: string;
  to?: string;
  count?: number;
  data_source?: string;
}

export async function fetchCandles(params: FetchCandlesParams): Promise<Candle[]> {
  const response = await apiClient.get<APIResponse<Candle[]>>('/api/v1/market/candles', {
    params: {
      symbol: params.symbol,
      timeframe: params.timeframe,
      from_time: params.from,
      to_time: params.to,
      count: params.count,
      data_source: params.data_source
    }
  });
  return response.data.data || [];
}
