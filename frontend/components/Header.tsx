'use client';

import React, { useEffect, useState } from 'react';
import { ProfileDropdown } from './ProfileDropdown';

import { Menu } from 'lucide-react';
import { useSidebar } from '@/context/SidebarContext';
import { getAccountSummary, AccountSummary } from '@/lib/api/execution';
import { getEquityCurve, EquityPoint } from '@/lib/api/dashboard';

export const Header = () => {
  const { toggleMobile } = useSidebar();
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [dailyPnl, setDailyPnl] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [accSummary, equityCurve] = await Promise.all([
          getAccountSummary().catch(() => null),
          getEquityCurve(1).catch(() => [] as EquityPoint[])
        ]);
        
        if (accSummary) {
          setSummary(accSummary);
        }

        if (equityCurve && equityCurve.length > 0) {
          // Get the latest day's PnL (today)
          const latest = equityCurve[equityCurve.length - 1];
          setDailyPnl(latest.daily_pnl);
        }
      } catch (error) {
        console.error('Failed to fetch header data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(num);
  };

  return (
    <header className="sticky top-0 z-40 w-full h-16 bg-gray-950/50 backdrop-blur-sm border-b border-gray-800 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleMobile}
          className="md:hidden p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors"
        >
          <Menu size={24} />
        </button>
        {/* Breadcrumbs or Page Title could go here */}
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/50 rounded-full border border-gray-800">
          <span className="text-xs text-gray-500">Equity</span>
          <span className="text-sm font-mono font-bold text-gray-200">
            {loading ? '...' : (summary?.NAV ? formatCurrency(summary.NAV) : '$0.00')}
          </span>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/50 rounded-full border border-gray-800">
          <span className="text-xs text-gray-500">PnL (24h)</span>
          <span className={`text-sm font-mono font-bold ${
            (dailyPnl || 0) >= 0 ? 'text-accent-green' : 'text-red-500'
          }`}>
            {loading ? '...' : ((dailyPnl || 0) > 0 ? '+' : '') + formatCurrency(dailyPnl || 0)}
          </span>
        </div>

        <button className="px-4 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs font-bold rounded border border-red-500/20 transition-colors">
          STOP ALL
        </button>

        <div className="h-6 w-px bg-gray-800 mx-2" />
        
        <ProfileDropdown />
      </div>
    </header>
  );
};
