"use client";

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getOpenInterestSnapshots, getOpenInterestDetails, OpenInterestSnapshot, OpenInterestRecord } from '@/lib/api/data';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { format } from 'date-fns';
import { Loader2, Flame } from 'lucide-react';

export function OpenInterestHeatmap() {
    const [snapshots, setSnapshots] = useState<OpenInterestSnapshot[]>([]);
    const [selectedSnapshot, setSelectedSnapshot] = useState<string>("");
    const [records, setRecords] = useState<OpenInterestRecord[]>([]);
    const [loading, setLoading] = useState(false);

    // Initial Load of Snapshots
    useEffect(() => {
        getOpenInterestSnapshots(10).then(data => {
            setSnapshots(data);
            if (data.length > 0) {
                setSelectedSnapshot(data[0].snapshot_at);
            }
        });
    }, []);

    // Listen for refresh events
    useEffect(() => {
        const handleRefresh = () => {
             getOpenInterestSnapshots(10).then(data => {
                setSnapshots(data);
                // If currently selected is gone, or empty, select first
                if (data.length > 0 && !selectedSnapshot) {
                    setSelectedSnapshot(data[0].snapshot_at);
                }
            });
        }
        window.addEventListener('refresh_oi_history', handleRefresh);
        return () => window.removeEventListener('refresh_oi_history', handleRefresh);
    }, [selectedSnapshot]);

    // Fetch Details when Snapshot changes
    useEffect(() => {
        if (!selectedSnapshot) return;

        setLoading(true);
        getOpenInterestDetails(selectedSnapshot)
            .then(data => setRecords(data))
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    }, [selectedSnapshot]);

    // Calculate Max Field Values for Color Intensity
    const { maxCall, maxPut } = useMemo(() => {
        let maxC = 0;
        let maxP = 0;
        records.forEach(r => {
            if (r.call_oi > maxC) maxC = r.call_oi;
            if (r.put_oi > maxP) maxP = r.put_oi;
        });
        return { maxCall: maxC, maxPut: maxP };
    }, [records]);

    return (
        <Card className="w-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl mt-6">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-orange-500/10 rounded-lg">
                        <Flame className="w-6 h-6 text-orange-500" />
                    </div>
                    <div>
                        <CardTitle className="text-xl">Open Interest Heatmap</CardTitle>
                        <CardDescription>Option Chain Distribution</CardDescription>
                    </div>
                </div>
                <div className="w-[250px]">
                    <Select value={selectedSnapshot} onValueChange={setSelectedSnapshot}>
                        <SelectTrigger className="bg-gray-900 border-gray-800 text-gray-300">
                            <SelectValue placeholder="Select Snapshot" />
                        </SelectTrigger>
                        <SelectContent>
                            {snapshots.map((s, idx) => (
                                <SelectItem key={idx} value={s.snapshot_at}>
                                    {format(new Date(s.snapshot_at), 'PPP p')}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </CardHeader>
            <CardContent>
                {loading || !selectedSnapshot ? (
                    <div className="flex justify-center items-center h-[400px]">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-500" />
                    </div>
                ) : (
                    <div className="rounded-md border border-gray-800 overflow-hidden">
                        <div className="grid grid-cols-12 bg-gray-900/80 p-3 text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800">
                             <div className="col-span-5 text-right pr-4">Call Open Interest</div>
                             <div className="col-span-2 text-center text-white">Strike</div>
                             <div className="col-span-5 pl-4">Put Open Interest</div>
                        </div>
                        <div className="max-h-[600px] overflow-y-auto custom-scrollbar">
                            {records.map((r, idx) => {
                                const callIntensity = maxCall > 0 ? (r.call_oi / maxCall) * 100 : 0;
                                const putIntensity = maxPut > 0 ? (r.put_oi / maxPut) * 100 : 0;

                                return (
                                    <div key={idx} className="grid grid-cols-12 border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors text-sm group">
                                         {/* Call Side */}
                                         <div className="col-span-5 relative flex items-center justify-end h-10 pr-4">
                                            <div 
                                                className="absolute top-1 bottom-1 right-0 bg-green-500/20 transition-all rounded-l-sm" 
                                                style={{ width: `${callIntensity}%` }}
                                            />
                                            <span className="relative z-10 font-mono text-green-400">
                                                {r.call_oi > 0 ? r.call_oi.toLocaleString() : '-'}
                                            </span>
                                         </div>

                                         {/* Strike */}
                                         <div className="col-span-2 flex items-center justify-center bg-gray-900/30 font-bold text-white border-x border-gray-800/50 group-hover:bg-gray-800/50 transition-colors">
                                            {r.strike}
                                         </div>

                                         {/* Put Side */}
                                         <div className="col-span-5 relative flex items-center justify-start h-10 pl-4">
                                             <div 
                                                className="absolute top-1 bottom-1 left-0 bg-red-500/20 transition-all rounded-r-sm" 
                                                style={{ width: `${putIntensity}%` }}
                                            />
                                            <span className="relative z-10 font-mono text-red-400">
                                                {r.put_oi > 0 ? r.put_oi.toLocaleString() : '-'}
                                            </span>
                                         </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
