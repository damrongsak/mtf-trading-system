'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getStrategyTemplates, createStrategy, getAccounts, getFunds, type LogicTemplate, type BrokerAccount } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function NewStrategyPage() {
    const router = useRouter();
    const [templates, setTemplates] = useState<LogicTemplate[]>([]);
    const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
    // const [funds, setFunds] = useState<Fund[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form State
    const [name, setName] = useState('My Strategy');
    const [selectedTemplate, setSelectedTemplate] = useState<string>('');
    const [selectedAccount, setSelectedAccount] = useState<string>('');
    const [selectedFund, setSelectedFund] = useState<string>('');
    const [symbol, setSymbol] = useState('EUR_USD');
    const [timeframe, setTimeframe] = useState('M15');
    const [riskUsd, setRiskUsd] = useState('10');

    useEffect(() => {
        const init = async () => {
            try {
                setLoading(true);
                const [tmpls, accts, fundsList] = await Promise.all([
                    getStrategyTemplates(),
                    getAccounts(),
                    getFunds()
                ]);
                
                setTemplates(tmpls);
                setAccounts(accts);
                // setFunds(fundsList);

                if (tmpls.length > 0) setSelectedTemplate(tmpls[0].id);
                if (accts.length > 0) setSelectedAccount(accts[0].id);
                if (fundsList.length > 0) setSelectedFund(fundsList[0].id);
                
            } catch (err) {
                console.error(err);
                setError("Failed to load configuration data");
            } finally {
                setLoading(false);
            }
        };
        init();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);

        if (!selectedFund) {
            setError("No fund selected. Please create a fund first.");
            setSubmitting(false);
            return;
        }

        try {
            await createStrategy({
                name,
                fund_id: selectedFund,
                template_id: selectedTemplate,
                broker_account_id: selectedAccount,
                config_json: {
                    symbol,
                    timeframe
                },
                risk_settings: {
                    max_risk_usd: parseFloat(riskUsd)
                }
            });
            router.push('/strategies');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create strategy');
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <Loader2 className="animate-spin h-8 w-8 text-primary" />
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto p-6 space-y-6">
            <Link href="/strategies" className="flex items-center text-muted-foreground hover:text-foreground">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Fleet
            </Link>

            <div>
                <h1 className="text-3xl font-bold tracking-tight">Launch New Strategy</h1>
                <p className="text-muted-foreground mt-2">Deploy a new automated trading bot to your fleet.</p>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Configuration</CardTitle>
                    <CardDescription>Define the operational parameters for this instance.</CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="name">Instance Name</Label>
                            <Input 
                                id="name" 
                                value={name} 
                                onChange={(e) => setName(e.target.value)} 
                                placeholder="e.g. Euro Scalper V1"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="template">Logic Template</Label>
                                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Template" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {templates.map(t => (
                                            <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="account">Broker Account</Label>
                                <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                                    <SelectTrigger disabled={accounts.length === 0}>
                                        <SelectValue placeholder={accounts.length === 0 ? "No Accounts Found" : "Select Account"} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {accounts.map(a => (
                                            <SelectItem key={a.id} value={a.id}>
                                                {a.broker_name} - {a.account_name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="symbol">Symbol</Label>
                                <Input 
                                    id="symbol" 
                                    value={symbol} 
                                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                    placeholder="EUR_USD"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="timeframe">Timeframe</Label>
                                <Select value={timeframe} onValueChange={setTimeframe}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="M5">M5</SelectItem>
                                        <SelectItem value="M15">M15</SelectItem>
                                        <SelectItem value="H1">H1</SelectItem>
                                        <SelectItem value="H4">H4</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="risk">Max Risk (USD)</Label>
                                <Input 
                                    id="risk" 
                                    type="number"
                                    min="1"
                                    max="100"
                                    value={riskUsd}
                                    onChange={(e) => setRiskUsd(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="pt-4">
                            <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                                {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                Launch Bot
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
