import React from 'react';
import { JournalStatsResponse } from '@/lib/api/types';
import { TrendingUp, TrendingDown, Percent, Activity, DollarSign, Scale } from 'lucide-react';

interface StatsCardsProps {
    stats: JournalStatsResponse;
}

const StatCard: React.FC<{
    title: string;
    value: string | number;
    subValue?: string;
    icon: React.ReactElement;
    trend?: 'up' | 'down' | 'neutral';
    color: string;
}> = ({ title, value, subValue, icon, trend, color }) => (
    <div className="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
        <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color}`}>
            {React.isValidElement(icon) && React.cloneElement(icon as React.ReactElement<{size?: number}>, { size: 64 })}
        </div>
        
        <div className="relative z-10">
            <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg bg-gray-700/50 text-${color.split('-')[1]}-400`}>
                    {icon}
                </div>
                <h3 className="text-gray-400 font-medium text-sm uppercase tracking-wider">{title}</h3>
            </div>
            
            <div className="text-3xl font-bold text-white tracking-tight">
                {value}
            </div>
            
            {subValue && (
                <div className={`mt-2 text-sm font-medium flex items-center gap-1 ${
                    trend === 'up' ? 'text-emerald-400' : 
                    trend === 'down' ? 'text-red-400' : 'text-gray-400'
                }`}>
                    {trend === 'up' && <TrendingUp size={14} />}
                    {trend === 'down' && <TrendingDown size={14} />}
                    {subValue}
                </div>
            )}
        </div>
    </div>
);

const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
                title="Net P&L"
                value={`$${stats.net_pnl.toFixed(2)}`}
                subValue={stats.net_pnl >= 0 ? "Profit" : "Loss"}
                icon={<DollarSign />}
                trend={stats.net_pnl >= 0 ? 'up' : 'down'}
                color={stats.net_pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}
            />
            
            <StatCard
                title="Win Rate"
                value={`${stats.win_rate.toFixed(1)}%`}
                subValue={`${stats.total_trades} Total Trades`}
                icon={<Percent />}
                trend={stats.win_rate > 50 ? 'up' : 'neutral'}
                color="text-blue-500"
            />
            
            <StatCard
                title="Profit Factor"
                value={stats.profit_factor.toFixed(2)}
                subValue={stats.profit_factor > 1.5 ? "Healthy" : "Needs Improvement"}
                icon={<Scale />}
                trend={stats.profit_factor > 1.0 ? 'up' : 'down'}
                color="text-purple-500"
            />
            
            <StatCard
                title="Avg R:R"
                value={`$${Math.abs(stats.avg_win).toFixed(0)} / $${Math.abs(stats.avg_loss).toFixed(0)}`}
                subValue={`Max DD: $${stats.max_drawdown.toFixed(0)}`}
                icon={<Activity />}
                trend="neutral"
                color="text-orange-500"
            />
        </div>
    );
};

export default StatsCards;
