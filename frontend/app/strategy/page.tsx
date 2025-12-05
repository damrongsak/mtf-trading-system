'use client';

import { StrategySection } from '@/components/settings/StrategySection';

export default function StrategyPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Strategy Configuration</h1>
          <p className="text-gray-400">
            Select and configure your trading strategy type and asset classes
          </p>
        </div>
        <StrategySection />
      </div>
    </div>
  );
}
