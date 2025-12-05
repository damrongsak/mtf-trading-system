'use client';

import { TradingPreferencesSection } from '@/components/settings/TradingPreferencesSection';

export default function TradingPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Trading Preferences</h1>
          <p className="text-gray-400">
            Configure your trading timeframes, symbols, and session preferences
          </p>
        </div>
        <TradingPreferencesSection />
      </div>
    </div>
  );
}
