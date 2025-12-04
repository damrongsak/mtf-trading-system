'use client';

import { useState } from 'react';
import { ProfileSection } from '@/components/settings/ProfileSection';
import { StrategySection } from '@/components/settings/StrategySection';
import { PortfolioSection } from '@/components/settings/PortfolioSection';
import { TradingPreferencesSection } from '@/components/settings/TradingPreferencesSection';

type TabType = 'profile' | 'strategy' | 'portfolio' | 'trading';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('profile');

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'strategy', label: 'Strategy', icon: '🎯' },
    { id: 'portfolio', label: 'Portfolio', icon: '📊' },
    { id: 'trading', label: 'Trading', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">
            Manage your profile, trading strategies, and portfolio preferences
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                px-6 py-3 font-medium transition-all duration-200
                border-b-2 flex items-center gap-2
                ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300'
                }
              `}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="animate-fade-in">
          {activeTab === 'profile' && <ProfileSection />}
          {activeTab === 'strategy' && <StrategySection />}
          {activeTab === 'portfolio' && <PortfolioSection />}
          {activeTab === 'trading' && <TradingPreferencesSection />}
        </div>
      </div>
    </div>
  );
}
