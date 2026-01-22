'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useDashboardStats } from '@/lib/hooks';
import { DashboardCard } from '@/components/dashboard/DashboardCard';
import { RecentSignalsCard } from '@/components/dashboard/RecentSignalsCard';
import { MarketStatusBadge } from '@/components/dashboard/MarketStatusBadge';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { AIAnalystCard } from '@/components/ai/AIAnalystCard';
import { OpenPositionsCard } from '@/components/dashboard/OpenPositionsCard';
import { MarketWatchCard } from '@/components/dashboard/MarketWatchCard';
import { DailyBriefingWidget } from '@/components/ai/DailyBriefingWidget';
import { getEquityCurve, getStrategyPerformance, StrategyPerformance, EquityPoint } from '@/lib/api/dashboard';
import { getAccountSummary, AccountSummary } from '@/lib/api/execution';
import { getPreferences } from '@/lib/api/settings';
import { useState, useEffect, useMemo } from 'react';
import { useLivePrices } from '@/lib/hooks/useLivePrices';
import { logger } from '@/lib/api/app-logger';

import { getStrategies } from '@/lib/api/strategies';
import { StrategyResponse } from '@/lib/api/types';

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  
  // Strategy State
  const [strategies, setStrategies] = useState<StrategyResponse[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('all');
  
  // Pass selectedStrategyId to stats hook
  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useDashboardStats(selectedStrategyId);
  const [equityData, setEquityData] = useState<EquityPoint[]>([]);
  const [equityLoading, setEquityLoading] = useState(true);
  const [accountSummary, setAccountSummary] = useState<AccountSummary | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [performance, setPerformance] = useState<StrategyPerformance[]>([]);
  
  // Note: signals hook removed as Card is autonomous

  // Live Prices Hook
  const allSymbols = useMemo(() => {
      // Create comprehensive symbol list for live pricing
      const symbols = new Set([
          ...watchlist.map(s => s.replace('/', '_')), 
          'EUR_USD', 'XAU_USD', 'GBP_USD', 'USD_JPY'
      ]);
      return Array.from(symbols);
  }, [watchlist]);
  
  const { prices, connected } = useLivePrices(allSymbols);
  
  // Load Strategies
  useEffect(() => {
      async function loadStrategies() {
          try {
              // Assuming generic query or fetch all
              // We use listHelper with fund_id=... but we don't have fund_id in context easily yet.
              // We'll use getStrategyPerformance to see names, but better to use strategiesApi.
              // Ideally we have a 'list all my strategies' endpoint.
              // Let's assume listHelper accepts optional fundId or we fetch from user preferences default fund.
              // For MVP, we will try to fetch default page.
              // Fetch all strategies available to the user
              // Fetch all strategies available to the user
              const res = await getStrategies();
              setStrategies(res);
          } catch (e) {
              logger.warn("Failed to load strategies list", e);
          }
      }
      loadStrategies();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setEquityLoading(true); // Set loading when strategy changes
      try {
        // ... (existing preferences logic) ...
        try {
            const prefs = await getPreferences();
             if (prefs.default_symbol) {
                 // Initialize watchlist with default symbol if empty
                 setWatchlist(prev => prev.length === 0 ? [prefs.default_symbol] : prev);
             }
        } catch (e) {
            logger.warn("Failed to load user preferences, using defaults", e);
        }

        const [eqData, accData, perfData] = await Promise.all([
            getEquityCurve(30, selectedStrategyId), // Pass ID
            getAccountSummary().catch(e => {
                logger.warn("Failed to fetch account summary:", e);
                return null;
            }),
            getStrategyPerformance().catch(e => {
                 logger.warn("Failed to fetch strategy performance:", e);
                 return [];
            })
        ]);
        setEquityData(eqData);
        setAccountSummary(accData);
        setPerformance(perfData);
      } catch (error) {
        logger.error('Failed to fetch dashboard data:', error);
      } finally {
        setEquityLoading(false);
      }
    };
    fetchData();
  }, [selectedStrategyId]); // Re-run when strategy changes

  const handleRefresh = async () => {
    await Promise.all([refetchStats()]);
  };

  // Show loading state
  if (authLoading || (statsLoading && !stats)) { // Allow stale data while loading new strategy stats? Or show loading.
    return (
      <div className="space-y-6">
        <div className="h-10 bg-gray-800/30 rounded-lg w-64 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-800/30 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-gray-800/30 rounded-xl animate-pulse" />
      </div>
    );
  }

  // Format currency
  const formatCurrency = (value: number) => {
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    });
    return formatter.format(value);
  };

  // Calculate PnL trend
  const pnlTrend = stats && stats.total_pnl > 0 ? 'up' : stats && stats.total_pnl < 0 ? 'down' : 'neutral';
  const winRateTrend = stats && stats.win_rate >= 60 ? 'up' : stats && stats.win_rate >= 40 ? 'neutral' : 'down';

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-blue to-accent-green bg-clip-text text-transparent">
            Welcome back, {user?.username || 'Trader'}
          </h1>
          <p className="text-gray-400 mt-1">Here&apos;s your trading overview</p>

          <Link href="/strategies/new" className="text-sm text-accent-blue hover:underline mt-2 inline-block">
             + New Strategy
          </Link>
        </div>
        
        <div className="flex items-center gap-4">
           {/* Strategy Selector */}
           <div className="relative">
              <select
                  value={selectedStrategyId}
                  onChange={(e) => setSelectedStrategyId(e.target.value)}
                  className="bg-gray-800 text-gray-200 border border-gray-700 rounded-lg py-2 px-4 pr-8 focus:outline-none focus:border-accent-blue appearance-none cursor-pointer text-sm"
              >
                  <option value="all">All Strategies</option>
                  {strategies.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.is_active ? 'Active' : 'Paused'})</option>
                  ))}
              </select>
               <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400">
                  <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                </div>
           </div>

          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            title="Refresh Dashboard"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <MarketStatusBadge />
        </div>
      </div>

      {/* Error States */}
      {statsError && (
        <div className="bg-red-400/10 border border-red-400/20 rounded-lg p-4 text-red-400 text-sm">
          Failed to load dashboard statistics: {statsError}
        </div>
      )}

      {/* Trading Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardCard
          title="Total P&L"
          value={formatCurrency(stats?.total_pnl || 0)}
          change={12.5}
          trend={pnlTrend}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        
        <DashboardCard
          title="Win Rate"
          value={stats?.win_rate.toFixed(1) || '0.0'}
          suffix="%"
          trend={winRateTrend}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        
        <DashboardCard
          title="Open Positions (Live)"
          value={accountSummary ? accountSummary.openPositionCount : (stats?.open_positions || 0)}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          }
        />
        
        <DashboardCard
          title="Total Trades"
          value={stats?.total_trades || 0}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          }
        />
      </div>

      {/* Main Content Area: Equity + Detail Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
            <EquityChart data={equityData} loading={equityLoading} />
            <OpenPositionsCard onRefresh={handleRefresh} prices={prices} connected={connected} />
            <RecentSignalsCard />
        </div>
        
        {/* Righht Column: AI & Performance */}
        <div className="space-y-6">
            <DailyBriefingWidget />
            <MarketWatchCard symbols={allSymbols} />
            <AIAnalystCard />
            
            <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-gray-200 mb-4">Strategy Performance</h3>
                <div className="space-y-4">
                    {performance.length > 0 ? (
                        performance.map((strat, idx) => (
                            <div key={idx} className="flex justify-between items-center">
                                <span className="text-gray-400 text-sm">{strat.strategy_name || 'Unknown'}</span>
                                <span className={`font-mono text-sm ${strat.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {strat.total_pnl >= 0 ? '+' : ''}{formatCurrency(strat.total_pnl)}
                                </span>
                            </div>
                        ))
                    ) : (
                        <div className="text-gray-500 text-sm text-center py-4">
                            No performance data available.
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>

      


      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          href="/journal/new"
          className="bg-gradient-to-r from-accent-blue/10 to-accent-green/10 border border-accent-blue/20 rounded-xl p-6 hover:border-accent-blue/40 transition-all duration-300 group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-accent-blue/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-100">New Journal Entry</h3>
              <p className="text-sm text-gray-400">Record your latest trade</p>
            </div>
          </div>
        </Link>
        {/* ... View Signals Link ... */}
        <Link
          href="/signals"
          className="bg-gradient-to-r from-accent-green/10 to-accent-blue/10 border border-accent-green/20 rounded-xl p-6 hover:border-accent-green/40 transition-all duration-300 group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-accent-green/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-100">View All Signals</h3>
              <p className="text-sm text-gray-400">Check current opportunities</p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
