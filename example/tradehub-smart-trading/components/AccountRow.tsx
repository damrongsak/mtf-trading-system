import React from 'react';
import { Account } from '../types';
import { MoreHorizontal } from 'lucide-react';

interface Props {
  account: Account;
}

const AccountRow: React.FC<Props> = ({ account }) => {
  const getFlag = (currency: string) => {
    switch (currency) {
      case 'AUD': return '🇦🇺';
      case 'JPY': return '🇯🇵';
      case 'EUR': return '🇪🇺';
      case 'USD': return '🇺🇸';
      default: return '🌐';
    }
  };

  const formatMoney = (amount: number, currency: string) => {
    // Basic formatting without symbol for cleaner look in dense table
    const formatted = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
    
    // Prefix logic
    const symbol = currency === 'JPY' ? '¥' : '$';
    return `${symbol}${formatted}`;
  };

  return (
    <div className="grid grid-cols-12 gap-4 py-4 px-6 border-gray-800 hover:bg-[#1c2129] transition-colors items-center group cursor-pointer">
      
      {/* Col 1: V20 / Flag */}
      <div className="col-span-1 flex items-center">
        <div className="relative">
          <div className="w-8 h-8 rounded-full bg-[#1A1E24] flex items-center justify-center text-lg border border-gray-700">
            {getFlag(account.currency)}
          </div>
          <div className="absolute -bottom-1 -right-2 bg-[#252b36] text-[9px] font-bold px-1 rounded border border-gray-600 text-slate-400 scale-90">
            {account.currency}
          </div>
        </div>
      </div>

      {/* Col 2: Account Details */}
      <div className="col-span-3">
        <div className="flex flex-col">
            <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                {account.type} • {account.mode}
                </span>
            </div>
            <h3 className="font-bold text-slate-200 text-sm leading-tight">{account.name}</h3>
            <p className="text-[11px] text-slate-500 font-mono mt-0.5">{account.accountNumber}</p>
        </div>
      </div>

      {/* Col 3: NAV */}
      <div className="col-span-2 text-right">
        <div className="text-slate-200 font-medium text-sm">{formatMoney(account.nav, account.currency)}</div>
      </div>

      {/* Col 4: Balance */}
      <div className="col-span-2 text-right">
        <div className="text-slate-200 font-medium text-sm">{formatMoney(account.balance, account.currency)}</div>
      </div>

      {/* Col 5: Unrealized P/L */}
      <div className="col-span-2 text-right">
        <div className={`text-sm font-medium ${account.unrealizedPL > 0 ? 'text-primary' : account.unrealizedPL < 0 ? 'text-red-400' : 'text-slate-200'}`}>
          {formatMoney(account.unrealizedPL, account.currency)}
        </div>
      </div>

      {/* Col 6: Margin */}
      <div className="col-span-1 text-right">
         <div className="text-slate-200 font-medium text-sm">{formatMoney(account.marginUsed, account.currency)}</div>
         <div className="text-[10px] text-slate-500">({account.marginPercent.toFixed(2)}% of NAV)</div>
      </div>

      {/* Col 7: Actions */}
      <div className="col-span-1 flex justify-end">
        <button className="text-slate-400 hover:text-white p-1 rounded hover:bg-white/10 transition-all">
          <MoreHorizontal size={20} />
        </button>
      </div>

    </div>
  );
};

export default AccountRow;