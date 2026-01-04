"use client";

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { getOpenInterestSnapshots, OpenInterestSnapshot } from '@/lib/api/data';
import { format } from 'date-fns';
import { Loader2, History, Database, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function OpenInterestHistory() {
    const [snapshots, setSnapshots] = useState<OpenInterestSnapshot[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSnapshots = async () => {
        try {
            setLoading(true);
            const data = await getOpenInterestSnapshots();
            setSnapshots(data);
            setError(null);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to fetch history");
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSnapshots();
    }, []);

    // Create a listener for refresh events from the upload component
    useEffect(() => {
        const handleRefresh = () => fetchSnapshots();
        window.addEventListener('refresh_oi_history', handleRefresh);
        return () => window.removeEventListener('refresh_oi_history', handleRefresh);
    }, []);

    // Error state is now handled inside the main render to keep the Refresh button visible

    return (
        <Card className="w-full h-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl flex flex-col">
            <CardHeader className="flex-none flex-row items-center justify-between space-y-0 pb-2">
                 <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/10 rounded-lg">
                         <Database className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                        <CardTitle className="text-xl">Historical Snapshots</CardTitle>
                        <CardDescription>Recently imported Open Interest datasets</CardDescription>
                    </div>
                </div>
                <Button variant="ghost" size="icon" onClick={fetchSnapshots} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto min-h-[300px] p-0">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-48 text-gray-500">
                        <Loader2 className="w-8 h-8 animate-spin mb-2" />
                        <p className="text-sm">Loading history...</p>
                    </div>
                ) : error ? (
                    <div className="flex flex-col items-center justify-center p-6 text-center space-y-4">
                        <div className="p-3 bg-red-500/10 rounded-full">
                            <AlertCircle className="w-6 h-6 text-red-500" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="font-semibold text-white">Failed to load history</h3>
                            <p className="text-sm text-gray-400 max-w-[250px] mx-auto">{error}</p>
                        </div>
                        <Button variant="outline" size="sm" onClick={fetchSnapshots} className="border-gray-700 hover:bg-gray-800">
                            Try Again
                        </Button>
                    </div>
                ) : snapshots.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-48 text-gray-500 border border-dashed border-gray-800 rounded-lg">
                        <History className="w-8 h-8 mb-2 opacity-50" />
                        <p className="text-sm">No historical data found</p>
                    </div>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow className="hover:bg-transparent border-gray-800">
                                <TableHead className="w-[180px]">Snapshot Date</TableHead>
                                <TableHead>Records</TableHead>
                                <TableHead className="text-right">Imported At</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {snapshots.map((snapshot, idx) => (
                                <TableRow key={idx} className="border-gray-800 hover:bg-gray-900/50 transition-colors">
                                    <TableCell className="font-medium text-white">
                                        {format(new Date(snapshot.snapshot_at), 'PPP p')}
                                    </TableCell>
                                    <TableCell>
                                        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                                            {snapshot.count.toLocaleString()} rows
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground text-xs">
                                        {format(new Date(snapshot.created_at), 'MMM d, HH:mm')}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </CardContent>
        </Card>
    );
}
