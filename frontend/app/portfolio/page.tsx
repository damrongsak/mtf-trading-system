'use client';

import { PortfolioSection } from '@/components/settings/PortfolioSection';

export default function PortfolioPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Portfolio Management</h1>
          <p className="text-gray-400">
            Manage your funds and configure risk parameters
          </p>
        </div>
        <PortfolioSection />
      </div>
    </div>
  );
}
