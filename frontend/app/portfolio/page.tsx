'use client';

import React, { useEffect, useState } from 'react';
import { getFunds } from '@/lib/api';
import { analyticsApi } from '@/lib/api/analytics';
import { Fund, AccountHistoryItem } from '@/lib/api/types';
import { logger } from '@/lib/api/app-logger';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PortfolioSection } from '@/components/settings/PortfolioSection';
import { FundOverviewCards } from '@/components/portfolio/FundOverviewCards';
import { EquityCurveChart } from '@/components/portfolio/EquityCurveChart';
import { MultiFundComparison } from '@/components/portfolio/MultiFundComparison';
import { HRPWeightsDisplay } from '@/components/institutional/HRPWeightsDisplay';
import { useAccount } from '@/context/AccountContext';

export default function PortfolioPage() {
  const { selectedAccount } = useAccount();
  const [funds, setFunds] = useState<Fund[]>([]);
  const [equityData, setEquityData] = useState<Record<string, AccountHistoryItem[]>>({});
  const [hrpWeights, setHrpWeights] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPortfolioData() {
      try {
        setLoading(true);
        const fundsData = await getFunds();
        setFunds(fundsData);

        // Fetch equity history per fund's broker accounts
        // Use the first owned fund's account for now
        if (selectedAccount) {
          const [historyRes, weightsRes] = await Promise.all([
            analyticsApi.getAccountHistory(selectedAccount.id, 200),
            analyticsApi.getHRPWeights(selectedAccount.fund_id)
          ]);
          
          // Group by fund name
          const fundName = fundsData.find(f => f.id === selectedAccount.fund_id)?.name || 'Primary';
          setEquityData({ [fundName]: historyRes.history });
          setHrpWeights(weightsRes.weights);
        }
      } catch (error) {
        logger.error('Failed to fetch portfolio data', error);
      } finally {
        setLoading(false);
      }
    }
    fetchPortfolioData();
  }, [selectedAccount]);

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-blue via-emerald-400 to-amber-400 bg-clip-text text-transparent">
            Portfolio Management
          </h1>
          <p className="text-gray-400 mt-1">
            Manage your funds, compare performance, and configure risk parameters
          </p>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="bg-gray-900/50 border border-gray-800 p-1 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="settings">Fund Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="space-y-6">
              {/* Summary Cards */}
              <FundOverviewCards funds={funds} loading={loading} />

              {/* Equity Curve + HRP Weights */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <EquityCurveChart data={equityData} loading={loading} />
                </div>
                <div>
                  <HRPWeightsDisplay weights={hrpWeights} loading={loading} />
                </div>
              </div>

              {/* Fund Comparison Table */}
              <MultiFundComparison funds={funds} loading={loading} />
            </div>
          </TabsContent>

          <TabsContent value="settings">
            <PortfolioSection />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
