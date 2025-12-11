'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useDashboardStats, useRecentSignals } from '@/lib/hooks';
import { DashboardCard } from '@/components/dashboard/DashboardCard';
import { RecentSignalsTable } from '@/components/dashboard/RecentSignalsTable';
import { MarketStatusBadge } from '@/components/dashboard/MarketStatusBadge';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { AIAnalystCard } from '@/components/ai/AIAnalystCard';
import { OpenPositionsCard } from '@/components/dashboard/OpenPositionsCard';
import { MarketWatchCard } from '@/components/dashboard/MarketWatchCard';
import { getEquityCurve, getStrategyPerformance, StrategyPerformance, EquityPoint } from '@/lib/api/dashboard';
import { getAccountSummary, AccountSummary } from '@/lib/api/execution';
import { getPreferences } from '@/lib/api/settings';
import { useState, useEffect } from 'react';
import { useLivePrices } from '@/lib/hooks/useLivePrices';

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useDashboardStats();
  const [equityData, setEquityData] = useState<EquityPoint[]>([]);
  const [equityLoading, setEquityLoading] = useState(true);
  const [accountSummary, setAccountSummary] = useState<AccountSummary | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [performance, setPerformance] = useState<StrategyPerformance[]>([]);
  
  const { signals, loading: signalsLoading, error: signalsError, refetch: refetchSignals } = useRecentSignals(5, watchlist);

  // Live Prices Hook - subscribe to major pairs + watchlist
  const allSymbols = Array.from(new Set([...watchlist, 'EUR_USD', 'XAU_USD', 'GBP_USD', 'USD_JPY']));
  const { prices, connected } = useLivePrices(allSymbols);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // First try to fetch preferences to set watchlist
        try {
            const prefs = await getPreferences();
            if (prefs.supported_symbols && prefs.supported_symbols.length > 0) {
                setWatchlist(prefs.supported_symbols);
            } else if (prefs.default_symbol) {
                setWatchlist([prefs.default_symbol]);
            }
        } catch (e) {
            console.warn("Failed to load user preferences, using defaults", e);
        }

        const [eqData, accData, perfData] = await Promise.all([
            getEquityCurve(),
            getAccountSummary().catch(e => {
                console.warn("Failed to fetch account summary (Execution Service might be offline or unconfigured):", e);
                return null;
            }),
            getStrategyPerformance().catch(e => {
                 console.warn("Failed to fetch strategy performance:", e);
                 return [];
            })
        ]);
        setEquityData(eqData);
        setAccountSummary(accData);
        setPerformance(perfData);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setEquityLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleRefresh = async () => {
    await Promise.all([refetchStats(), refetchSignals()]);
  };

  // Show loading state
  if (authLoading || statsLoading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="h-10 bg-gray-800/30 rounded-lg w-64 animate-pulse" />
        
        {/* Cards Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-800/30 rounded-xl animate-pulse" />
          ))}
        </div>
        
        {/* Table Skeleton */}
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
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-blue to-accent-green bg-clip-text text-transparent">
            Welcome back, {user?.username || 'Trader'}
          </h1>
          <p className="text-gray-400 mt-1">Here&apos;s your trading overview</p>
        </div>
        <div className="flex items-center gap-4">
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
            <RecentSignalsTable signals={signals} loading={signalsLoading} />
        </div>
        
        {/* Righht Column: AI & Performance */}
        <div className="space-y-6">
            <MarketWatchCard symbols={allSymbols} prices={prices} connected={connected} />
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

      {/* Recent Signals */}
      {signalsError && (
        <div className="bg-red-400/10 border border-red-400/20 rounded-lg p-4 text-red-400 text-sm">
          Failed to load recent signals: {signalsError}
        </div>
      )}
      


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
