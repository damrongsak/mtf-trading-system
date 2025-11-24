import React, { useEffect, useState } from 'react';
import { Account } from '../types';
import AccountRow from './AccountRow';
import { 
  Info, 
  Download, 
  ExternalLink, 
  ChevronRight, 
  BookOpen, 
  Smartphone, 
  Monitor, 
  Globe,
  ArrowUpDown
} from 'lucide-react';
import { getPortfolioInsight } from '../services/geminiService';

const mockAccounts: Account[] = [
  {
    id: '1',
    name: 'SWING01',
    accountNumber: '001-011-437083-005',
    currency: 'AUD',
    nav: 182.31,
    balance: 182.31,
    unrealizedPL: 0.00,
    marginUsed: 0.00,
    marginPercent: 0.00,
    type: 'V20',
    mode: 'NETTING'
  },
  {
    id: '2',
    name: 'Damrongsak_NRTC21',
    accountNumber: '001-011-437083-004',
    currency: 'AUD',
    nav: 0.00,
    balance: 0.00,
    unrealizedPL: 0.00,
    marginUsed: 0.00,
    marginPercent: 0.00,
    type: 'MT4',
    mode: 'NETTING'
  },
  {
    id: '3',
    name: 'Damrongsak-v20 MT4 H',
    accountNumber: '001-011-437083-003',
    currency: 'AUD',
    nav: 0.01,
    balance: 0.01,
    unrealizedPL: 0.00,
    marginUsed: 0.00,
    marginPercent: 0.00,
    type: 'MT4',
    mode: 'NETTING'
  },
  {
    id: '4',
    name: 'Damrongsak-v20 MT4 H',
    accountNumber: '001-011-437083-002',
    currency: 'AUD',
    nav: 0.03,
    balance: 0.03,
    unrealizedPL: 0.00,
    marginUsed: 0.00,
    marginPercent: 0.00,
    type: 'V20',
    mode: 'NETTING'
  },
  {
    id: '5',
    name: 'JPY Trading',
    accountNumber: '001-011-437083-001',
    currency: 'JPY',
    nav: 0,
    balance: 0,
    unrealizedPL: 0,
    marginUsed: 0,
    marginPercent: 0.00,
    type: 'V20',
    mode: 'NETTING'
  }
];

const Dashboard: React.FC = () => {
  const [insight, setInsight] = useState<string>('');
  const [platformTab, setPlatformTab] = useState<'v20' | 'MT4'>('v20');

  useEffect(() => {
    // Simulate fetching insight on mount
    getPortfolioInsight(182.37, 0).then(setInsight);
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-background p-4 sm:p-8 font-sans">
      
      {/* Welcome Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-10 gap-6">
        <div>
          <h1 className="text-3xl font-light text-slate-200 mb-2">Hello, Damrongsak!</h1>
          {insight && (
            <p className="text-sm text-primary/80 flex items-center gap-2">
               AI Insight: <span className="text-slate-400 italic">"{insight}"</span>
            </p>
          )}
        </div>

        <div className="flex gap-4 w-full lg:w-auto">
          <button className="flex-1 lg:flex-none border border-slate-600 text-slate-300 hover:border-slate-400 hover:text-white font-medium px-8 py-2 rounded transition-all text-sm uppercase tracking-wide">
            Transfer
          </button>
          <button className="flex-1 lg:flex-none border border-slate-600 text-slate-300 hover:border-slate-400 hover:text-white font-medium px-8 py-2 rounded transition-all text-sm uppercase tracking-wide">
            Withdraw
          </button>
          <button className="flex-1 lg:flex-none bg-accentBlue text-white hover:bg-blue-600 font-medium px-8 py-2 rounded shadow-lg shadow-blue-900/40 transition-all text-sm uppercase tracking-wide">
            Deposit
          </button>
        </div>
      </div>

      {/* Main Content Layout: 2 Columns on Large Screens */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Accounts Table (Approx 75% width) */}
        <div className="lg:col-span-8 xl:col-span-9">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-2xl font-semibold text-white">Accounts</h2>
            <span className="bg-primary text-black text-[10px] font-bold px-1.5 py-0.5 rounded uppercase">Live</span>
            <p className="ml-auto text-[10px] text-slate-500 hidden sm:block uppercase tracking-wider">Data Updated: 24 Nov 2025, 9:32 AM</p>
          </div>

          <div className="bg-surface rounded border border-gray-800 overflow-hidden min-w-[800px] lg:min-w-0">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 py-3 px-6 bg-[#1A1E24] border-b border-gray-800 text-[11px] font-bold text-slate-500 uppercase tracking-wider items-center">
              <div className="col-span-1 flex items-center gap-1 group cursor-pointer hover:text-slate-300">
                V20 <Info size={12} className="opacity-50 group-hover:opacity-100" />
              </div>
              <div className="col-span-3 flex items-center gap-1 cursor-pointer hover:text-slate-300">
                Account <ArrowUpDown size={10} />
              </div>
              <div className="col-span-2 text-right">NAV</div>
              <div className="col-span-2 text-right">Balance</div>
              <div className="col-span-2 text-right">Unrealized P/L</div>
              <div className="col-span-1 text-right">Margin Used</div>
              <div className="col-span-1 flex justify-end">
                <button className="border border-slate-600 rounded px-2 py-0.5 text-slate-400 hover:text-white hover:border-white transition-colors text-[10px]">
                    Trade
                </button>
              </div>
            </div>

            {/* Rows */}
            <div className="divide-y divide-gray-800 bg-surface">
              {mockAccounts.map(acc => (
                <AccountRow key={acc.id} account={acc} />
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Widgets (Approx 25% width) */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-6">
          
          <div className="bg-surface rounded-lg border border-gray-800 overflow-hidden flex flex-col">
            <div className="p-5 pb-2">
                <h3 className="font-semibold text-white text-base">Trading Platforms</h3>
            </div>
            
            <div className="px-5 pb-5">
                {/* Promo Banner */}
                <div className="bg-gradient-to-r from-[#1e2329] to-[#252b36] rounded-lg p-4 mb-5 border border-gray-700/50 relative overflow-hidden group">
                    <div className="flex items-start gap-3 relative z-10">
                        <div className="w-10 h-10 bg-gradient-to-br from-primary to-emerald-600 rounded-lg flex items-center justify-center text-black shadow-lg shrink-0">
                            <span className="font-bold text-lg">T</span>
                        </div>
                        <div>
                            <p className="text-white text-xs font-semibold mb-1">OANDA mobile app</p>
                            <a href="#" className="text-accentBlue text-sm font-bold hover:underline flex items-center gap-1">
                            Download Now
                            </a>
                            <p className="text-[10px] text-slate-500 mt-1">Supports all types of trading accounts</p>
                        </div>
                    </div>
                </div>

                <p className="text-xs text-slate-400 mb-3">Check out which platforms are available for your different account types</p>

                {/* Switcher */}
                <div className="bg-[#0b0e11] p-1 rounded-full flex mb-6 border border-gray-800">
                    <button 
                        onClick={() => setPlatformTab('v20')}
                        className={`flex-1 py-1.5 text-xs font-medium rounded-full transition-all ${platformTab === 'v20' ? 'bg-slate-700 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        v20
                    </button>
                    <button 
                        onClick={() => setPlatformTab('MT4')}
                        className={`flex-1 py-1.5 text-xs font-medium rounded-full transition-all ${platformTab === 'MT4' ? 'bg-slate-700 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        v20 MT4
                    </button>
                </div>

                {/* Platform List */}
                <div className="space-y-1">
                    <a href="#" className="flex items-center gap-3 p-2 rounded hover:bg-[#252a33] text-slate-300 hover:text-white transition-colors group">
                        <Smartphone size={18} className="text-slate-500 group-hover:text-primary transition-colors" />
                        <span className="text-sm">OANDA mobile app</span>
                    </a>
                    <a href="#" className="flex items-center gap-3 p-2 rounded hover:bg-[#252a33] text-slate-300 hover:text-white transition-colors group">
                        <Globe size={18} className="text-slate-500 group-hover:text-primary transition-colors" />
                        <span className="text-sm">OANDA Web Platform</span>
                    </a>
                    <a href="#" className="flex items-center gap-3 p-2 rounded hover:bg-[#252a33] text-slate-300 hover:text-white transition-colors group">
                        <Monitor size={18} className="text-slate-500 group-hover:text-primary transition-colors" />
                        <span className="text-sm">OANDA Desktop</span>
                    </a>
                    <a href="#" className="flex items-center gap-3 p-2 rounded hover:bg-[#252a33] text-slate-300 hover:text-white transition-colors group">
                        <div className="w-[18px] h-[18px] flex items-center justify-center font-bold text-[10px] border border-slate-500 rounded text-slate-500 group-hover:border-primary group-hover:text-primary transition-colors">T</div>
                        <span className="text-sm">TradingView</span>
                    </a>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-800">
                    <button className="flex items-center gap-2 text-slate-400 hover:text-white text-xs font-medium transition-colors">
                        <BookOpen size={14} /> Platform user guide
                    </button>
                </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Dashboard;