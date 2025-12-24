'use client';

import { useState, useEffect } from 'react';
import { getStrategies, stopStrategy, startStrategy, type StrategyResponse } from '@/lib/api/strategies';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, Play, Square, AlertCircle, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchStrategies = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getStrategies();
      setStrategies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load strategies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleToggle = async (id: string, currentlyActive: boolean) => {
    try {
        setProcessingId(id);
        if (currentlyActive) {
            await stopStrategy(id);
        } else {
            await startStrategy(id);
        }
        // Optimistic update or refetch
        await fetchStrategies();
    } catch (err) {
        alert("Failed to toggle strategy: " + (err instanceof Error ? err.message : String(err)));
    } finally {
        setProcessingId(null);
    }
  };

  if (loading && strategies.length === 0) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="animate-spin h-8 w-8 text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
            <h1 className="text-3xl font-bold tracking-tight">Active Strategies</h1>
            <p className="text-muted-foreground mt-2">Manage your fleet of automated trading bots.</p>
        </div>
        <div className="flex gap-2">
            <Button variant="outline" onClick={fetchStrategies} disabled={loading}>
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
            </Button>
            <Link href="/strategies/new">
                <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Launch Strategy
                </Button>
            </Link>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {strategies.length === 0 && !error ? (
        <Card className="text-center py-10">
            <CardHeader>
                <CardTitle>No Active Strategies</CardTitle>
                <CardDescription>You haven't launched any strategies yet.</CardDescription>
            </CardHeader>
            <CardContent>
                <Link href="/strategies/new">
                    <Button variant="outline">Create Your First Bot</Button>
                </Link>
            </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {strategies.map((strategy) => (
            <Card key={strategy.id} className="relative overflow-hidden">
                {strategy.is_active && (
                    <div className="absolute top-0 right-0 w-2 h-full bg-green-500/20" />
                )}
              <CardHeader className="pb-4">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-xl">{strategy.name}</CardTitle>
                        <CardDescription className="font-mono text-xs mt-1">
                            {strategy.template_id}
                        </CardDescription>
                    </div>
                    <Badge variant={strategy.is_active ? "default" : "secondary"}>
                        {strategy.is_active ? "RUNNING" : "STOPPED"}
                    </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">Symbol:</div>
                    <div className="font-medium text-right">{strategy.config_json?.symbol || 'N/A'}</div>
                    
                    <div className="text-muted-foreground">Timeframe:</div>
                    <div className="font-medium text-right">{strategy.config_json?.timeframe || 'N/A'}</div>
                    
                    <div className="text-muted-foreground">Risk:</div>
                    <div className="font-medium text-right text-red-400">
                        ${strategy.risk_settings?.max_risk_usd || '10.00'}
                    </div>
                </div>

                <div className="pt-4 flex gap-2">
                    <Button 
                        className="w-full" 
                        variant={strategy.is_active ? "destructive" : "default"}
                        onClick={() => handleToggle(strategy.id, strategy.is_active)}
                        disabled={!!processingId}
                    >
                        {processingId === strategy.id ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : strategy.is_active ? (
                            <><Square className="mr-2 h-4 w-4 fill-current" /> Stop</>
                        ) : (
                            <><Play className="mr-2 h-4 w-4 fill-current" /> Start</>
                        )}
                    </Button>
                    {/* Add Config/Edit button later */}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
