import React from 'react';
import { PatternAnalysisResponse, PatternItem } from '@/lib/api/types';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { AlertTriangle, Brain, Zap } from 'lucide-react';

interface PatternsGridProps {
    patterns: PatternAnalysisResponse;
}

const COLORS = {
    A_GAME: '#10b981', // Emerald
    B_GAME: '#f59e0b', // Amber
    C_GAME: '#ef4444', // Red
    DEFAULT: '#6b7280'
};

const GameLevelChart: React.FC<{ data: PatternItem[] }> = ({ data }) => {
    const chartData = data.map(item => ({
        ...item,
        color: (COLORS as any)[item.name] || COLORS.DEFAULT
    }));

    if (chartData.length === 0) return <div className="text-gray-500 text-center py-10">No Game Level data</div>;

    return (
        <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="count"
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                        ))}
                    </Pie>
                    <RechartsTooltip 
                        contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '0.5rem' }}
                        itemStyle={{ color: '#e5e7eb' }}
                    />
                    <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};

const PatternList: React.FC<{ title: string; icon: React.ReactNode; data: PatternItem[]; color: string }> = ({ title, icon, data, color }) => (
    <div className="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
            <div className={`p-2 rounded-lg bg-gray-700/50 ${color}`}>
                {icon}
            </div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
        </div>
        
        <div className="space-y-4">
            {data.length === 0 ? (
                <div className="text-gray-500 text-sm">No patterns detected yet.</div>
            ) : (
                data.map((item, idx) => (
                    <div key={idx} className="relative">
                        <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-300 font-medium">{item.name}</span>
                            <span className="text-gray-400">{item.count} times</span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                            <div 
                                className={`h-2 rounded-full ${color.replace('text-', 'bg-').replace('-400', '-500')}`}
                                style={{ width: `${Math.min((item.count / Math.max(...data.map(d => d.count))) * 100, 100)}%` }}
                            ></div>
                        </div>
                    </div>
                ))
            )}
        </div>
    </div>
);

const PatternsGrid: React.FC<PatternsGridProps> = ({ patterns }) => {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Game Level Distribution */}
            <div className="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-gray-700/50 text-emerald-400">
                        <Zap size={20} />
                    </div>
                    <h3 className="text-lg font-semibold text-white">Game Level Analysis</h3>
                </div>
                <GameLevelChart data={patterns.game_levels} />
            </div>

            {/* Top Emotions */}
            <PatternList 
                title="Top Emotional Triggers" 
                icon={<Brain size={20} />} 
                data={patterns.top_emotions} 
                color="text-purple-400"
            />

            {/* Top Mistakes */}
            <PatternList 
                title="Recurring Mistakes" 
                icon={<AlertTriangle size={20} />} 
                data={patterns.top_mistakes} 
                color="text-red-400"
            />
        </div>
    );
};

export default PatternsGrid;
