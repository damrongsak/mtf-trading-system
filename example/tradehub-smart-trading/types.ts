export interface Account {
  id: string;
  name: string;
  accountNumber: string;
  currency: 'AUD' | 'USD' | 'JPY' | 'EUR';
  nav: number;
  balance: number;
  unrealizedPL: number;
  marginUsed: number;
  marginPercent: number;
  type: 'V20' | 'MT4';
  mode: 'NETTING' | 'HEDGING';
}

export interface NavItem {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  subItems?: string[];
  isOpen?: boolean;
}

export interface GeminiAnalysis {
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  summary: string;
  keyPoints: string[];
}