'use client';

import { ProfileSection } from '@/components/settings/ProfileSection';
import { BrokerAccountsSection } from '@/components/settings/BrokerAccountsSection';

export default function SettingsPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">
            Manage your account information, preferences, and broker connections
          </p>
        </div>
        
        <div className="space-y-8">
            <ProfileSection />
            <BrokerAccountsSection />
        </div>
      </div>
    </div>
  );
}
