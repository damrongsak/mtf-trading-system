'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSidebar } from '@/context/SidebarContext';
import {
  LayoutDashboard,
  Target,
  Briefcase,
  Settings as SettingsIcon,
  TrendingUp,
  BookOpen,
  CreditCard,
  FlaskConical,
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  Atom,
  ClipboardList,
  Terminal,
  Rocket,
} from 'lucide-react';

type NavItem = {
  name: string;
  href: string;
  icon: React.ElementType;
};

type NavCategory = {
  name: string;
  icon: React.ElementType;
  items: NavItem[];
};

const navCategories: NavCategory[] = [
  {
    name: 'OVERVIEW',
    icon: LayoutDashboard,
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'AI Analyst', href: '/ai-analyst', icon: Bot },
      { name: 'Market Watch', href: '/market', icon: TrendingUp },
    ],
  },
  {
    name: 'STRATEGY',
    icon: Target,
    items: [
      { name: 'Library', href: '/strategies', icon: Target },
      { name: 'Editor', href: '/strategies/editor', icon: Terminal },
      { name: 'Backtest', href: '/backtest', icon: FlaskConical },
      { name: 'GRID Lab', href: '/simulation', icon: Atom },
    ],
  },
  {
    name: 'TRADING',
    icon: Rocket,
    items: [
      { name: 'Live Deployments', href: '/deployments', icon: Rocket },
      { name: 'Signals', href: '/signals', icon: TrendingUp },
      { name: 'Portfolio', href: '/portfolio', icon: Briefcase },
      { name: 'Settings', href: '/trading', icon: SettingsIcon },
    ],
  },
  {
    name: 'JOURNAL',
    icon: BookOpen,
    items: [
      { name: 'Journal', href: '/journal', icon: BookOpen },
      { name: 'History', href: '/trades', icon: ClipboardList },
      { name: 'Transactions', href: '/transactions', icon: CreditCard },
    ],
  },
  {
    name: 'ACCOUNT',
    icon: User,
    items: [
      { name: 'Profile', href: '/settings', icon: User },
    ],
  },
];

export const Sidebar = () => {
  const pathname = usePathname();
  
  // Start with default expanded state to match server-side rendering
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['OVERVIEW', 'STRATEGY', 'TRADING', 'ANALYSIS', 'ACCOUNT']);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize from localStorage on mount (client-only)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('expandedCategories');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            setExpandedCategories(parsed);
          }
        } catch (e) {
          console.error("Failed to parse sidebar categories", e);
        }
      }
      setIsInitialized(true);
    }
  }, []);

  // Save to localStorage whenever expanded state changes, but only after initialization
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('expandedCategories', JSON.stringify(expandedCategories));
    }
  }, [expandedCategories, isInitialized]);

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories((prev) => {
      if (prev.includes(categoryName)) {
        return prev.filter((c) => c !== categoryName);
      } else {
        return [...prev, categoryName];
      }
    });
  };

  const isCategoryExpanded = (categoryName: string) => {
    return expandedCategories.includes(categoryName);
  };

  const { isMobileOpen, closeMobile } = useSidebar();

  const handleLinkClick = () => {
    // Close sidebar on mobile when a link is clicked
    if (window.innerWidth < 768) {
      closeMobile();
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={closeMobile}
        />
      )}

      <aside 
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-gray-950/95 backdrop-blur-md border-r border-gray-800 
          flex flex-col transition-transform duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'} 
          md:translate-x-0 md:shadow-none
        `}
      >
        {/* Logo/Brand */}
        <div className="p-6 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-tr from-accent-blue to-accent-green rounded-lg flex items-center justify-center font-bold text-white text-xl shadow-lg">
              M
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                MTF Trader
              </h1>
              <p className="text-xs text-gray-500 font-mono">v0.1.0-alpha</p>
            </div>
          </div>
          {/* Close button for mobile inside drawer */}
          <button onClick={closeMobile} className="md:hidden text-gray-400 hover:text-white">
            <ChevronRight className="rotate-180" size={24} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navCategories.map((category) => {
            const isExpanded = isCategoryExpanded(category.name);
            const CategoryIcon = category.icon;
            
            return (
              <div key={category.name} className="mb-2">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category.name)}
                  className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-bold text-gray-500 hover:text-gray-400 transition-colors group"
                >
                  <div className="flex items-center gap-2">
                    <CategoryIcon size={14} className="text-gray-600 group-hover:text-gray-500" />
                    <span className="tracking-wide">{category.name}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown size={14} className="text-gray-600" />
                  ) : (
                    <ChevronRight size={14} className="text-gray-600" />
                  )}
                </button>

                {/* Category Items */}
                {isExpanded && (
                  <div className="mt-1 space-y-0.5">
                    {category.items.map((item) => {
                      const isActive = pathname === item.href;
                      const ItemIcon = item.icon;
                      
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          onClick={handleLinkClick}
                          className={`
                            flex items-center gap-3 pl-12 pr-4 py-2.5 text-sm font-medium transition-all duration-200
                            border-l-4 
                            ${
                              isActive
                                ? 'border-accent-blue text-white bg-accent-blue/10'
                                : 'border-transparent text-gray-400 hover:text-white hover:bg-gray-800/50'
                            }
                          `}
                        >
                          <ItemIcon size={18} className={isActive ? 'text-accent-blue' : ''} />
                          <span>{item.name}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Status Footer */}
        <div className="p-4 border-t border-gray-800 mt-auto">
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <div className="flex items-center gap-2 mb-1.5">
              <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse shadow-lg shadow-green-500/50" />
              <span className="text-xs text-gray-400 font-medium">System Online</span>
            </div>
            <div className="text-xs text-gray-600 font-mono">
              Latency: 24ms
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
