'use client';

import { TradingPreferencesSection } from '@/components/settings/TradingPreferencesSection';
import { BrokerAccountsSection } from '@/components/settings/BrokerAccountsSection';

export default function TradingPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Trading Configuration</h1>
          <p className="text-gray-400">
            Manage your broker accounts, timeframes, and session preferences
          </p>
        </div>
        
        <div className="space-y-8">
          <BrokerAccountsSection />
          <TradingPreferencesSection />
        </div>
      </div>
    </div>
  );
}
