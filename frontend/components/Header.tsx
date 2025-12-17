'use client';

import React from 'react';
import { ProfileDropdown } from './ProfileDropdown';

import { Menu } from 'lucide-react';
import { useSidebar } from '@/context/SidebarContext';

export const Header = () => {
  const { toggleMobile } = useSidebar();

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
          <span className="text-sm font-mono font-bold text-gray-200">$10,450.00</span>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/50 rounded-full border border-gray-800">
          <span className="text-xs text-gray-500">PnL (24h)</span>
          <span className="text-sm font-mono font-bold text-accent-green">+$124.50</span>
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
