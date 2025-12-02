'use client';

import React from 'react';

interface DashboardCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  suffix?: string;
}

export const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  value,
  change,
  icon,
  trend = 'neutral',
  suffix = '',
}) => {
  const trendColor = trend === 'up' ? 'text-accent-green' : trend === 'down' ? 'text-red-400' : 'text-gray-400';
  const trendBg = trend === 'up' ? 'bg-accent-green/10' : trend === 'down' ? 'bg-red-400/10' : 'bg-gray-400/10';

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 hover:border-accent-blue/30 transition-all duration-300">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-sm text-gray-400 font-medium">{title}</p>
        </div>
        {icon && (
          <div className="text-accent-blue/60">
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2 mb-2">
        <h3 className="text-3xl font-bold text-gray-100">
          {value}
          {suffix && <span className="text-gray-400 text-xl ml-1">{suffix}</span>}
        </h3>
      </div>

      {/* Change indicator */}
      {change !== undefined && (
        <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${trendBg} ${trendColor}`}>
          {trend === 'up' && (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          )}
          {trend === 'down' && (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          )}
          <span>{Math.abs(change)}%</span>
        </div>
      )}
    </div>
  );
};
