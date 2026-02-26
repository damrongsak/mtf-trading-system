import React, { useState } from 'react';
import { 
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger 
} from '@/components/ui/dialog';
import { useIndicatorStore, IndicatorType, ActiveIndicator } from '@/lib/store/indicatorStore';
import { Settings2, Plus, Trash2, Eye, EyeOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

const INDICATOR_TEMPLATES: Record<IndicatorType, { name: string, defaultParams: Record<string, number | string | boolean>, defaultColor: string }> = {
    'EMA': { name: 'Exponential Moving Average', defaultParams: { period: 50 }, defaultColor: '#3b82f6' },
    'RSI': { name: 'Relative Strength Index', defaultParams: { period: 14 }, defaultColor: '#a855f7' },
    'MACD': { name: 'MACD', defaultParams: { fast: 12, slow: 26, signal: 9 }, defaultColor: '#06b6d4' },
    'ATR': { name: 'Average True Range', defaultParams: { period: 14 }, defaultColor: '#ec4899' },
    'ADX': { name: 'Average Directional Index', defaultParams: { period: 14 }, defaultColor: '#eab308' },
    'SMC': { name: 'Smart Money Concepts', defaultParams: { lookbackOB: 5, lookbackStructure: 15 }, defaultColor: '#22c55e' },
    'GAMMA': { name: 'Gamma Levels', defaultParams: {}, defaultColor: '#f97316' }
};

export function IndicatorConfigModal({ children }: { children: React.ReactNode }) {
    const { indicators, addIndicator, updateIndicator, removeIndicator, toggleVisibility } = useIndicatorStore();
    const [open, setOpen] = useState(false);
    
    // Component to render specific inputs based on the indicator type's params
    const ParamEditor = ({ ind }: { ind: ActiveIndicator }) => {
        return (
            <div className="grid grid-cols-2 gap-2 mt-2">
                {Object.entries(ind.params).map(([key, value]) => (
                    <div key={key} className="flex flex-col gap-1">
                        <label className="text-xs text-gray-400 uppercase">{key}</label>
                        <input 
                            type="number"
                            value={typeof value === 'boolean' ? (value ? 1 : 0) : value}
                            onChange={(e) => {
                                const newVal = parseFloat(e.target.value) || 0;
                                updateIndicator(ind.id, { params: { ...ind.params, [key]: newVal } });
                            }}
                            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
                        />
                    </div>
                ))}
            </div>
        );
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px] bg-[#0a0a0a] border-gray-800 text-white p-0 overflow-hidden">
                <DialogHeader className="p-4 border-b border-white/5 bg-gray-950/50">
                    <DialogTitle className="flex items-center gap-2">
                        <Settings2 size={18} className="text-blue-500" />
                        Indicators and Strategies
                    </DialogTitle>
                </DialogHeader>

                <div className="flex flex-col h-[500px]">
                    {/* Add New Section */}
                    <div className="p-4 border-b border-white/5 bg-gray-900/20">
                        <div className="flex gap-2">
                            <Select 
                                onValueChange={(val: string) => {
                                    const indicatorType = val as IndicatorType;
                                    const template = INDICATOR_TEMPLATES[indicatorType];
                                    addIndicator(indicatorType, template.defaultParams, template.defaultColor);
                                }}
                            >
                                <SelectTrigger className="w-full bg-gray-900 border-gray-700 text-sm">
                                    <SelectValue placeholder="Add an indicator..." />
                                </SelectTrigger>
                                <SelectContent className="bg-gray-900 border-gray-800">
                                    {Object.entries(INDICATOR_TEMPLATES).map(([key, template]) => (
                                        <SelectItem key={key} value={key}>{template.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Active Indicators List */}
                    <ScrollArea className="flex-1 p-4">
                        <div className="flex flex-col gap-4 pb-4">
                            {indicators.length === 0 ? (
                                <div className="text-center text-sm text-gray-500 py-8">
                                    No indicators active.
                                </div>
                            ) : (
                                indicators.map((ind) => (
                                    <div key={ind.id} className="bg-gray-900/50 border border-white/5 rounded-lg p-3 group">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: ind.color || '#fff' }} />
                                                <span className="font-bold text-sm tracking-wide">
                                                    {ind.type} {ind.params.period ? ind.params.period : ''}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-1 opacity-50 group-hover:opacity-100 transition-opacity">
                                                <input 
                                                    type="color" 
                                                    value={ind.color || '#3b82f6'}
                                                    onChange={(e) => updateIndicator(ind.id, { color: e.target.value })}
                                                    className="w-6 h-6 p-0 border-0 rounded cursor-pointer bg-transparent"
                                                />
                                                <button 
                                                    onClick={() => toggleVisibility(ind.id)}
                                                    className="p-1.5 hover:bg-white/10 rounded"
                                                >
                                                    {ind.visible ? <Eye size={14} /> : <EyeOff size={14} className="text-gray-500" />}
                                                </button>
                                                <button 
                                                    onClick={() => removeIndicator(ind.id)}
                                                    className="p-1.5 hover:bg-rose-500/10 hover:text-rose-400 rounded transition-colors text-gray-500"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                        {Object.keys(ind.params).length > 0 && (
                                            <ParamEditor ind={ind} />
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </div>
            </DialogContent>
        </Dialog>
    );
}
