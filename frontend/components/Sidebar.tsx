'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { name: 'Dashboard', href: '/' },
  { name: 'Signals', href: '/signals' },
  { name: 'Journal', href: '/journal' },
  { name: 'Backtest', href: '/backtest' },
  { name: 'AI Analyst', href: '/ai-analyst' },
  { name: 'Settings', href: '/settings' },
];

export const Sidebar = () => {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gray-950/80 backdrop-blur-md border-r border-gray-800 flex flex-col z-50">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-accent-blue to-accent-green bg-clip-text text-transparent">
          MTF Trader
        </h1>
        <p className="text-xs text-gray-500 mt-1 font-mono">v0.1.0-alpha</p>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                block px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200
                ${isActive 
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20' 
                  : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
                }
              `}
            >
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
            <span className="text-xs text-gray-400 font-mono">System Online</span>
          </div>
          <div className="text-xs text-gray-600 font-mono">
            Latency: 24ms
          </div>
        </div>
      </div>
    </aside>
  );
};
