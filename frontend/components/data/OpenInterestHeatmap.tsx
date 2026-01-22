"use client";

import { useEffect, useState, useMemo, memo, CSSProperties } from 'react';
import { logger } from '@/lib/api/app-logger';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getOpenInterestDetails, OpenInterestRecord } from '@/lib/api/data';
import { Loader2, Flame } from 'lucide-react';
import { cn } from '@/lib/utils';

interface OpenInterestHeatmapProps {
    snapshotAt: string;
    // Optional filters to apply to the heatmap data
    contract?: string;
    minOi?: number;
    maxOi?: number;
}

interface HeatmapItemData {
    filteredRecords: OpenInterestRecord[];
    maxCall: number;
    maxPut: number;
}

interface HeatmapRowProps {
    data: HeatmapItemData;
    index: number;
    style: CSSProperties;
}

// Memoized Row Component
const HeatmapRow = memo(({ data, index, style }: HeatmapRowProps) => {
    const { filteredRecords, maxCall, maxPut } = data;
    const r = filteredRecords[index];
    
    if (!r) return null;

    const callIntensity = maxCall > 0 ? (r.call_oi / maxCall) * 100 : 0;
    const putIntensity = maxPut > 0 ? (r.put_oi / maxPut) * 100 : 0;

    return (
        <div style={style} className="grid grid-cols-12 border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors text-sm group items-center">
             <div className="col-span-1 text-[10px] text-slate-500 flex items-center justify-center font-mono">
                {r.contract_symbol}
             </div>
             {/* Call Side */}
             <div className="col-span-4 relative flex items-center justify-end h-8 pr-4">
                <div 
                    className="absolute top-1 bottom-1 right-0 bg-green-500/20 transition-all rounded-l-sm" 
                    style={{ width: `${callIntensity}%` }}
                />
                <span className={cn("relative z-10 font-mono", r.call_oi > 0 ? "text-green-400" : "text-gray-600")}>
                    {r.call_oi > 0 ? r.call_oi.toLocaleString() : '-'}
                </span>
             </div>

             {/* Strike */}
             <div className="col-span-2 flex items-center justify-center bg-gray-900/30 font-bold text-white border-x border-gray-800/50 h-full group-hover:bg-gray-800/50 transition-colors">
                {r.strike}
             </div>

             {/* Put Side */}
             <div className="col-span-4 relative flex items-center justify-start h-8 pl-4">
                 <div 
                    className="absolute top-1 bottom-1 left-0 bg-red-500/20 transition-all rounded-r-sm" 
                    style={{ width: `${putIntensity}%` }}
                />
                <span className={cn("relative z-10 font-mono", r.put_oi > 0 ? "text-red-400" : "text-gray-600")}>
                    {r.put_oi > 0 ? r.put_oi.toLocaleString() : '-'}
                </span>
             </div>
             
              <div className="col-span-1"></div>
        </div>
    );
});
HeatmapRow.displayName = 'HeatmapRow';

export function OpenInterestHeatmap({ snapshotAt, contract, minOi = 0, maxOi }: OpenInterestHeatmapProps) {
    const [records, setRecords] = useState<OpenInterestRecord[]>([]);
    const [loading, setLoading] = useState(false);

    // Fetch Details when Snapshot or Contract changes (Debounced)
    useEffect(() => {
        if (!snapshotAt) return;

        const timer = setTimeout(() => {
            setLoading(true);
            // Use Smart Filter by default for optimized loading
            // Pass contract to backend to filter early
            const queryContract = (contract === "ALL_CONTRACTS_VALUE_RESET") ? undefined : contract;

            getOpenInterestDetails(snapshotAt, queryContract, minOi, maxOi, true)
                .then(data => setRecords(data))
                .catch(err => logger.error(err))
                .finally(() => setLoading(false));
        }, 500);

        return () => clearTimeout(timer);
    }, [snapshotAt, contract, minOi, maxOi]);

    // Derived filtered records (Sorting only, filtering handled by backend)
    const filteredRecords = useMemo(() => {
        const res = records;
        
        // Backend handles Contract & Smart Range filtering now.
        // Backend also handles Min/Max OI filtering.
        // We just need to sort.
        
        return res.sort((a,b) => a.strike - b.strike);
    }, [records]);

    // Calculate Max Field Values for Color Intensity
    const { maxCall, maxPut } = useMemo(() => {
        let maxC = 0;
        let maxP = 0;
        filteredRecords.forEach(r => {
            if (r.call_oi > maxC) maxC = r.call_oi;
            if (r.put_oi > maxP) maxP = r.put_oi;
        });
        return { maxCall: maxC, maxPut: maxP };
    }, [filteredRecords]);

    const itemData = useMemo<HeatmapItemData>(() => ({
        filteredRecords,
        maxCall,
        maxPut
    }), [filteredRecords, maxCall, maxPut]);



    if (!snapshotAt) return null;

    return (
        <Card className="w-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl mt-6 flex flex-col h-[600px]">
            <CardHeader className="flex flex-row items-center justify-between pb-2 shrink-0">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-orange-500/10 rounded-lg">
                        <Flame className="w-6 h-6 text-orange-500" />
                    </div>
                    <div>
                        <CardTitle className="text-xl">Open Interest Heatmap</CardTitle>
                        <CardDescription>
                            {contract && contract !== "ALL_CONTRACTS_VALUE_RESET" ? contract : "All Contracts"} | 
                            Smart Range Active | Range: {minOi} - {maxOi || "Max"} | Total Levels: {filteredRecords.length}
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 pb-2">
                {loading ? (
                    <div className="flex justify-center items-center h-full">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-500" />
                    </div>
                ) : (
                    <div className="rounded-md border border-gray-800 overflow-hidden h-full flex flex-col">
                        <div className="grid grid-cols-12 bg-gray-900/80 p-3 text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800 shrink-0 z-10">
                             <div className="col-span-1 text-center">Expiry</div>
                             <div className="col-span-4 text-right pr-4">Call OI</div>
                             <div className="col-span-2 text-center text-white">Strike</div>
                             <div className="col-span-4 pl-4">Put OI</div>
                             <div className="col-span-1"></div>
                        </div>
                        
                        <div className="flex-1 w-full min-h-0 bg-transparent relative">
                             {filteredRecords.length === 0 ? (
                                <div className="flex items-center justify-center h-full text-slate-500">No levels found in this range.</div>
                            ) : (
                                <div className="h-full w-full">
                                    <div className="h-full w-full overflow-auto custom-scrollbar">
                                        {filteredRecords.map((record, index) => (
                                            <HeatmapRow 
                                                key={`${record.contract_symbol}-${record.strike}`} 
                                                data={itemData} 
                                                index={index} 
                                                style={{ height: 40, width: '100%' }} 
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
