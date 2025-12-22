import { apiClient } from './client';

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
}

export async function fetchCandles(params: FetchCandlesParams): Promise<Candle[]> {
  const response = await apiClient.get<{ data: Candle[] }>('/api/v1/market/candles', {
    params: {
      symbol: params.symbol,
      timeframe: params.timeframe,
      from_time: params.from,
      to_time: params.to,
      count: params.count
    }
  });
  console.log('FetchCandles Response:', response.data);
  return response.data.data;
}
