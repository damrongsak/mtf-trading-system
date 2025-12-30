
"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, Square, Activity, AlertTriangle } from 'lucide-react';
import { getDeployments, stopDeployment, restartDeployment } from '@/lib/api/deployments';
import { ConfirmationModal } from '@/components/ui/confirmation-modal';
import { Deployment } from '@/lib/api/types';
import { format } from 'date-fns';
import { Pagination } from '@/components/common';

export default function DeploymentsPage() {
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [processingId, setProcessingId] = useState<string | null>(null);
    const [processingAction, setProcessingAction] = useState<'stop' | 'restart' | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [stopModalOpen, setStopModalOpen] = useState(false);
    const [errorModalOpen, setErrorModalOpen] = useState(false);

    const [selectedDeploymentId, setSelectedDeploymentId] = useState<string | null>(null);

    // Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [limit, setLimit] = useState(10);

    const fetchDeployments = async () => {
        try {
            const response = await getDeployments(currentPage, limit);
            setDeployments(response.data);
            setTotalPages(response.meta.total_pages || 1);
            setTotal(response.meta.total || 0);
            setError(null);
        } catch (err) {
            setError("Failed to load deployments.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchDeployments();
        const interval = setInterval(fetchDeployments, 5000); // Poll status every 5s
        return () => clearInterval(interval);
    }, [currentPage]); // Re-fetch on page change

    const handleRestartClick = async (id: string) => {
        setProcessingId(id);
        setProcessingAction('restart');
        try {
            await restartDeployment(id);
            await fetchDeployments();
        } catch (err: any) {
             // Extract error message if possible
            const msg = err.response?.data?.detail || "Failed to restart deployment";
            setError(msg);
            setErrorModalOpen(true);
        } finally {
            setProcessingId(null);
            setProcessingAction(null);
        }
    };

    const handleStopClick = (id: string) => {
        setSelectedDeploymentId(id);
        setStopModalOpen(true);
    };

    const handleConfirmStop = async () => {
        if (!selectedDeploymentId) return;
        
        setProcessingId(selectedDeploymentId); 
        setProcessingAction('stop');
        
        try {
            await stopDeployment(selectedDeploymentId);
            await fetchDeployments();
            setStopModalOpen(false);
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Failed to stop deployment";
            setError(msg);
            setErrorModalOpen(true);
        } finally {
            setProcessingId(null);
            setProcessingAction(null);
        }
    };

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                        Fleet Command
                    </h1>
                    <p className="text-slate-400 mt-2">Manage your active algorithmic trading instances.</p>
                </div>
                
                {/* Stats */}
                <Card className="bg-slate-900 border-slate-800">
                    <CardContent className="p-4 flex gap-6">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-white">{deployments.filter(d => d.status === 'ACTIVE').length}</div>
                            <div className="text-xs text-slate-500 uppercase">Active</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-white">{deployments.length}</div>
                            <div className="text-xs text-slate-500 uppercase">Total</div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-md flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5" />
                    {error}
                </div>
            )}

            <Card className="bg-slate-950 border-slate-800">
                <CardHeader>
                    <CardTitle className="text-lg">Active Instances</CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading && deployments.length === 0 ? (
                        <div className="flex justify-center p-12">
                            <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
                        </div>
                    ) : deployments.length === 0 ? (
                        <div className="text-center p-12 text-slate-500">
                            <Activity className="h-12 w-12 mx-auto mb-4 opacity-20" />
                            <p>No active deployments found.</p>
                            <p className="text-sm mt-2">Deploy a strategy from the Editor.</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="border-slate-800 hover:bg-slate-900/50">
                                    <TableHead className="text-slate-400">ID</TableHead>
                                    <TableHead className="text-slate-400">Mode</TableHead>
                                    <TableHead className="text-slate-400">Strategy Name</TableHead>
                                    <TableHead className="text-slate-400">Symbol</TableHead>
                                    <TableHead className="text-slate-400">Timeframe</TableHead>
                                    <TableHead className="text-slate-400">Status</TableHead>
                                    <TableHead className="text-slate-400 text-right">PnL</TableHead>
                                    <TableHead className="text-slate-400">Started At</TableHead>
                                    <TableHead className="text-right text-slate-400">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {deployments.map((dep) => (
                                    <TableRow key={dep.id} className="border-slate-800 hover:bg-slate-900/50">
                                        <TableCell className="font-mono text-xs text-slate-500">
                                            {dep.id.slice(0, 8)}...
                                        </TableCell>
                                        <TableCell>
                                            {dep.is_live ? (
                                                <Badge variant="destructive" className="bg-red-500/20 text-red-400 hover:bg-red-500/30">LIVE</Badge>
                                            ) : (
                                                <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30">PAPER</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="font-medium text-white">{dep.strategy_name || dep.id.slice(0, 8)}</TableCell>
                                        <TableCell className="font-medium text-slate-300">{dep.stock_symbol}</TableCell>
                                        <TableCell className="text-slate-400">{dep.timeframe}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <div className={`h-2 w-2 rounded-full ${
                                                    dep.status === 'ACTIVE' ? 'bg-emerald-500 animate-pulse' : 
                                                    dep.status === 'ERROR' ? 'bg-red-500' :
                                                    'bg-slate-500'
                                                }`} />
                                                <span className={`text-sm ${
                                                    dep.status === 'ACTIVE' ? 'text-emerald-400' : 
                                                    dep.status === 'ERROR' ? 'text-red-400' :
                                                    'text-slate-500'
                                                }`}>
                                                    {dep.status}
                                                </span>
                                            </div>
                                            {dep.last_error && (
                                                <div className="text-[10px] text-red-500 mt-1 truncate max-w-[200px]" title={dep.last_error}>
                                                    {dep.last_error}
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell className={`text-right font-mono ${
                                            (dep.total_pnl_usd || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                                        }`}>
                                            ${(dep.total_pnl_usd || 0).toFixed(2)}
                                        </TableCell>
                                        <TableCell className="text-slate-500 text-xs">
                                            {format(new Date(dep.started_at), 'MMM dd HH:mm')}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex gap-2 justify-end">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        disabled={!['STOPPED', 'STOPPING', 'ERROR'].includes(dep.status) || processingId === dep.id}
                                                        onClick={() => handleRestartClick(dep.id)}
                                                        className={`border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 ${
                                                            !['STOPPED', 'STOPPING', 'ERROR'].includes(dep.status) ? 'opacity-50 cursor-not-allowed' : ''
                                                        }`}
                                                    >
                                                        {processingId === dep.id && processingAction === 'restart' ? (
                                                            <Loader2 className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <>
                                                                <Play className="h-4 w-4 mr-1 fill-current" /> Start
                                                            </>
                                                        )}
                                                    </Button>
                                                <Button 
                                                    variant="outline" 
                                                    size="sm"
                                                    disabled={['STOPPED', 'STOPPING'].includes(dep.status) || processingId === dep.id}
                                                    onClick={() => handleStopClick(dep.id)}
                                                    className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                                                >
                                                    {processingId === dep.id && processingAction === 'stop' ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <>
                                                            <Square className="h-4 w-4 mr-1 fill-current" /> Stop
                                                        </>
                                                    )}
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <Pagination 
                currentPage={currentPage}
                totalPages={totalPages}
                perPage={limit}
                total={total}
                onPageChange={setCurrentPage}
                onPerPageChange={setLimit}
            />

            <ConfirmationModal 
                isOpen={stopModalOpen}
                onClose={() => setStopModalOpen(false)}
                onConfirm={handleConfirmStop}
                title="Stop Deployment"
                message="Are you sure you want to stop this trading bot? Open positions will NOT be closed automatically."
                confirmText="Stop Bot"
                variant="danger"
                isLoading={!!processingId}
            />

            <ConfirmationModal
                isOpen={errorModalOpen}
                onClose={() => setErrorModalOpen(false)}
                onConfirm={() => setErrorModalOpen(false)}
                title="Error"
                message={error || "An unexpected error occurred."}
                confirmText="Close"
                showCancel={false}
                variant="default"
            />
        </div>
    );
}
