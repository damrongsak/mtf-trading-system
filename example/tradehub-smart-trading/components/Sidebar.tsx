import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  Wallet, 
  PieChart, 
  Settings, 
  ChevronDown, 
  ChevronRight,
  Landmark,
  FileText
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({
    'manageFunds': true
  });

  const toggleMenu = (key: string) => {
    setOpenMenus(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const NavItem = ({ 
    icon: Icon, 
    label, 
    hasSubmenu = false, 
    menuKey = '', 
    active = false 
  }: { 
    icon: any, 
    label: string, 
    hasSubmenu?: boolean, 
    menuKey?: string, 
    active?: boolean 
  }) => (
    <div className="mb-1">
      <button 
        onClick={() => hasSubmenu && toggleMenu(menuKey)}
        className={`w-full flex items-center justify-between px-4 py-3 text-sm font-medium transition-colors border-l-4 ${
          active 
            ? 'border-primary text-white bg-surfaceHighlight' 
            : 'border-transparent text-slate-400 hover:text-white hover:bg-[#1A1E24]'
        }`}
      >
        <div className="flex items-center gap-3">
          <Icon size={18} />
          <span>{label}</span>
        </div>
        {hasSubmenu && (
          openMenus[menuKey] ? <ChevronDown size={14} /> : <ChevronRight size={14} />
        )}
      </button>
      
      {hasSubmenu && openMenus[menuKey] && (
        <div className="bg-[#0b0e11] py-1">
          {['Deposit', 'Withdraw', 'Transfer', 'Bank Accounts'].map((sub) => (
            <button key={sub} className="w-full text-left pl-14 pr-4 py-2 text-sm text-slate-500 hover:text-white transition-colors">
              {sub}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <aside className="hidden md:flex flex-col w-64 bg-surface border-r border-gray-800 h-screen sticky top-0 overflow-y-auto">
      <div className="p-6 flex items-center gap-2 mb-2">
        {/* Logo Placeholder */}
        <div className="w-8 h-8 bg-gradient-to-tr from-green-400 to-blue-500 rounded-lg flex items-center justify-center font-bold text-white text-xl">
          T
        </div>
        <span className="font-bold text-xl tracking-tight text-white">TradeHub</span>
      </div>

      <nav className="flex-1">
        <NavItem icon={LayoutDashboard} label="Dashboard" active={true} />
        <NavItem icon={Wallet} label="Accounts" />
        
        <NavItem 
          icon={Landmark} 
          label="Manage funds" 
          hasSubmenu={true} 
          menuKey="manageFunds" 
        />
        
        <div className="my-2 border-t border-gray-800 mx-4"></div>
        
        <NavItem icon={FileText} label="Reports" />
        <NavItem icon={Settings} label="Profile settings" />
      </nav>

      <div className="p-4 text-xs text-slate-600 text-center">
        v2.4.0-stable
      </div>
    </aside>
  );
};

export default Sidebar;