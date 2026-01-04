'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileSection } from '@/components/settings/ProfileSection';
import { PluginManagement } from '@/components/settings/PluginManagement';
import { DataSourcesSection } from '@/components/settings/DataSourcesSection';
import { BrokerAccountsSection } from '@/components/settings/BrokerAccountsSection';
import { TradingPreferencesSection } from '@/components/settings/TradingPreferencesSection';
import { User, Settings, Briefcase, Cpu, Database } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">
            Manage your account, trading preferences, broker connections, data sources, and plugins.
          </p>
        </div>
        
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="bg-gray-900 border border-gray-800 p-1">
            <TabsTrigger value="profile" className="data-[state=active]:bg-gray-800">
              <User className="w-4 h-4 mr-2" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="trading" className="data-[state=active]:bg-gray-800">
              <Settings className="w-4 h-4 mr-2" />
              Trading
            </TabsTrigger>
            <TabsTrigger value="brokerage" className="data-[state=active]:bg-gray-800">
              <Briefcase className="w-4 h-4 mr-2" />
              Brokerage
            </TabsTrigger>
             <TabsTrigger value="datasources" className="data-[state=active]:bg-gray-800">
              <Database className="w-4 h-4 mr-2" />
              Data Sources
            </TabsTrigger>
            <TabsTrigger value="plugins" className="data-[state=active]:bg-gray-800">
              <Cpu className="w-4 h-4 mr-2" />
              Plugins
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-6 animate-fade-in">
            <ProfileSection />
          </TabsContent>

          <TabsContent value="trading" className="space-y-6 animate-fade-in">
             <TradingPreferencesSection />
          </TabsContent>

          <TabsContent value="brokerage" className="space-y-6 animate-fade-in">
             <BrokerAccountsSection />
          </TabsContent>

          <TabsContent value="datasources" className="space-y-6 animate-fade-in">
             <DataSourcesSection />
          </TabsContent>

          <TabsContent value="plugins" className="space-y-6 animate-fade-in">
            <PluginManagement />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}


