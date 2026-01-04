'use client';

import { BrokerReferenceDashboard } from '@/components/trading/BrokerReferenceDashboard';

export default function TradingPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Trading Reference</h1>
          <p className="text-gray-400">
            Global Support Reference: Live instrument specifications from your broker.
          </p>
        </div>
        
        <div className="space-y-8 animate-fade-in">
          <BrokerReferenceDashboard />
        </div>
      </div>
    </div>
  );
}
