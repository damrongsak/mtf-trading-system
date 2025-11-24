import React from 'react';
import { Bell, HelpCircle, User, Settings, Menu } from 'lucide-react';

interface HeaderProps {
  toggleMobileMenu: () => void;
}

const Header: React.FC<HeaderProps> = ({ toggleMobileMenu }) => {
  return (
    <header className="h-16 bg-surface border-b border-gray-800 flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="flex items-center gap-4">
        <button className="md:hidden text-slate-400" onClick={toggleMobileMenu}>
          <Menu size={24} />
        </button>
        
        {/* Trade / Hub Toggle */}
        <div className="hidden sm:flex bg-black/40 p-1 rounded-lg">
          <button className="px-4 py-1.5 text-sm font-medium text-slate-400 hover:text-white transition-colors">
            Trade
          </button>
          <button className="px-4 py-1.5 text-sm font-medium bg-primary text-black rounded shadow-sm">
            Hub
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4 sm:gap-6">
        <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium">
          <Settings size={18} />
          <span className="hidden sm:inline">Trading Tools</span>
        </button>

        <div className="h-6 w-px bg-gray-700 hidden sm:block"></div>

        <button className="text-slate-400 hover:text-white transition-colors relative">
          <Bell size={20} />
          <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border border-surface"></span>
        </button>
        
        <button className="text-slate-400 hover:text-white transition-colors">
          <HelpCircle size={20} />
        </button>

        <div className="flex items-center gap-3 pl-2">
          <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center text-xs font-bold text-white border border-gray-600 cursor-pointer">
            DS
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;