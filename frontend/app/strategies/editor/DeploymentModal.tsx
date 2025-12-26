
import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, Rocket, AlertTriangle, ShieldCheck } from 'lucide-react';
import { createDeployment } from '@/lib/api/deployments';
import { useRouter } from 'next/navigation';

interface DeploymentModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    strategyId: string | null;
    initialConfig: any;
    onSuccess?: () => void;
}

export function DeploymentModal({ open, onOpenChange, strategyId, initialConfig, onSuccess }: DeploymentModalProps) {
    const router = useRouter();
    const [isLive, setIsLive] = useState(false);
    const [symbol, setSymbol] = useState(initialConfig?.symbol || "XAU/USD");
    const [timeframe, setTimeframe] = useState(initialConfig?.timeframe || "M15");
    const [isDeploying, setIsDeploying] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDeploy = async () => {
        if (!strategyId) return;
        
        setIsDeploying(true);
        setError(null);

        try {
            await createDeployment({
                strategy_id: strategyId,
                stock_symbol: symbol,
                timeframe: timeframe,
                config_snapshot: initialConfig,
                is_live: isLive
            });

            onOpenChange(false);
            if (onSuccess) onSuccess();
            
            // Redirect to deployments page
            router.push('/deployments');
            
        } catch (err: any) {
            setError(err.message || "Failed to deploy strategy");
        } finally {
            setIsDeploying(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="bg-slate-900 border-slate-800 text-slate-100 sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Rocket className="h-5 w-5 text-purple-500" />
                        Deploy Strategy
                    </DialogTitle>
                    <DialogDescription>
                        Configure your deployment parameters.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* Mode Selection */}
                    <div className={`p-4 rounded-lg border flex items-center justify-between ${isLive ? 'bg-red-950/20 border-red-900/50' : 'bg-emerald-950/20 border-emerald-900/50'}`}>
                        <div className="space-y-1">
                            <Label className="text-base font-semibold">
                                {isLive ? "Live Trading Mode" : "Paper Trading Mode"}
                            </Label>
                            <p className="text-xs text-slate-400">
                                {isLive 
                                    ? "Executing with REAL funds. Risk is not zero." 
                                    : "Simulated execution. No real funds at risk."}
                            </p>
                        </div>
                        <Switch 
                            checked={isLive}
                            onCheckedChange={setIsLive} 
                            className={`${isLive ? 'bg-red-600' : 'bg-emerald-600'}`}
                        />
                    </div>

                    {isLive && (
                        <Alert className="bg-red-950/30 border-red-900 text-red-400">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>Warning</AlertTitle>
                            <AlertDescription className="text-xs">
                                Ensure risk limits are configured correctly in the strategy editor before deploying. 
                                Max risk per trade is hardcapped at $10 for this account tier.
                            </AlertDescription>
                        </Alert>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Symbol</Label>
                            <Input 
                                value={symbol} 
                                onChange={(e) => setSymbol(e.target.value)}
                                className="bg-slate-950 border-slate-800"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Timeframe</Label>
                            <Select value={timeframe} onValueChange={setTimeframe}>
                                <SelectTrigger className="bg-slate-950 border-slate-800">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-900 border-slate-800 text-slate-100">
                                    {["M1", "M5", "M15", "H1", "H4", "D"].map(tf => (
                                        <SelectItem key={tf} value={tf}>{tf}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    
                    {error && (
                        <div className="text-sm text-red-500 bg-red-500/10 p-2 rounded">
                            {error}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button 
                        onClick={handleDeploy} 
                        disabled={isDeploying || !strategyId}
                        className={isLive ? "bg-red-600 hover:bg-red-700" : "bg-purple-600 hover:bg-purple-700"}
                    >
                        {isDeploying ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Deploying...
                            </>
                        ) : (
                            <>
                                <Rocket className="mr-2 h-4 w-4" />
                                {isLive ? "Deploy Live" : "Deploy Paper"}
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
