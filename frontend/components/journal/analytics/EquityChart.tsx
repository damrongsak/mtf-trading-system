import React from 'react';
import { EquityCurvePoint } from '@/lib/api/types';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EquityChartProps {
    data: EquityCurvePoint[];
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: any[];
    label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-gray-900/90 backdrop-blur border border-gray-700 p-3 rounded-lg shadow-xl">
                <p className="text-gray-400 text-xs mb-1">{label ? new Date(label).toLocaleString() : ''}</p>
                <p className="text-emerald-400 font-bold text-lg">
                    ${payload[0].value.toFixed(2)}
                </p>
                <p className={`text-xs ${payload[0].payload.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {payload[0].payload.pnl >= 0 ? '+' : ''}{payload[0].payload.pnl.toFixed(2)} PnL
                </p>
            </div>
        );
    }
    return null;
};

const EquityChart: React.FC<EquityChartProps> = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center text-gray-500 bg-gray-800/30 rounded-xl border border-gray-700/50">
                Not enough data to display chart
            </div>
        );
    }

    // Note: The provided Code Edit snippet for 'chartData' seems to be for a different chart type
    // (e.g., multi-line chart with 'name' property and 'COLORS' constant).
    // For this single AreaChart, 'data' can be used directly.
    // If 'chartData' transformation is truly needed, 'COLORS' and 'item.name' would need to be defined/adapted.
    // As per the instruction to make the change faithfully, I'm placing it where it was indicated,
    // but commenting it out as it would cause a runtime error without 'COLORS' and 'item.name' in EquityCurvePoint.
    // If the intent was to introduce a multi-series chart, further changes would be required.

    return (
        <div className="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 h-96">
            <h3 className="text-lg font-semibold text-white mb-4">Equity Curve</h3>
            <div className="h-full w-full">
                <ResponsiveContainer width="100%" height="90%">
                    {/* const chartData = data.map(item => ({
                        ...item,
                        color: (COLORS as Record<string, string>)[item.name] || COLORS.DEFAULT
                    })); */}
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                        <XAxis 
                            dataKey="timestamp" 
                            stroke="#9ca3af" 
                            tick={{fontSize: 12}}
                            tickFormatter={(value) => new Date(value).toLocaleDateString()}
                            minTickGap={30}
                        />
                        <YAxis 
                            stroke="#9ca3af" 
                            tick={{fontSize: 12}}
                            tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area 
                            type="monotone" 
                            dataKey="balance" 
                            stroke="#10b981" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorBalance)" 
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default EquityChart;
