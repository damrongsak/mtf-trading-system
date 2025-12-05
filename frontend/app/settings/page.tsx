'use client';

import { ProfileSection } from '@/components/settings/ProfileSection';

export default function SettingsPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Profile Settings</h1>
          <p className="text-gray-400">
            Manage your account information and preferences
          </p>
        </div>
        <ProfileSection />
      </div>
    </div>
  );
}
