'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Plus, Trash2, ShieldCheck, AlertCircle, Edit2, RefreshCw } from "lucide-react";
import { getAccounts, createAccount, deleteAccount, updateAccount, fetchBrokerSymbols } from '@/lib/api/accounts';
import { BrokerAccount, BrokerAccountCreate } from '@/lib/api/types';
import { ConfirmationModal } from "@/components/ui/confirmation-modal";
import { TagsInput } from "@/components/ui/tags-input";

    interface BrokerAccountsSectionProps {
        fundId?: string | null;
    }

    export function BrokerAccountsSection({ fundId }: BrokerAccountsSectionProps) {
    const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
    const [loading, setLoading] = useState(true);
    const [isAdding, setIsAdding] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Delete Modal State
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    // Save Confirmation State
    const [showSaveConfirm, setShowSaveConfirm] = useState(false);
    const [pendingData, setPendingData] = useState<BrokerAccountCreate | null>(null);

    // Form State
    const [brokerName, setBrokerName] = useState('OANDA');
    const [accountName, setAccountName] = useState('');
    const [accountNumber, setAccountNumber] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [supportedSymbolsInput, setSupportedSymbolsInput] = useState('');
    const [riskSettingsInput, setRiskSettingsInput] = useState('');
    const [isLive, setIsLive] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Edit State
    const [editingAccount, setEditingAccount] = useState<BrokerAccount | null>(null);
    const [editSymbols, setEditSymbols] = useState<string[]>([]);
    const [isFetchingSymbols, setIsFetchingSymbols] = useState(false);

    const fetchAccounts = useCallback(async () => {
        try {
            setLoading(true);
            const data = await getAccounts();
            if (fundId) {
                setAccounts(data.filter(acc => acc.fund_id === fundId));
            } else {
                setAccounts(data);
            }
        } catch (err) {
            console.error(err);
            setError("Failed to load accounts");
        } finally {
            setLoading(false);
        }
    }, [fundId]);

    useEffect(() => {
        fetchAccounts();
    }, [fetchAccounts]);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);

        try {
            // 1. Format Validation
            if (brokerName === 'OANDA') {
                const oandaPattern = /^\d{3}-\d{3}-\d+-\d{3}$/;
                if (!oandaPattern.test(accountNumber)) {
                     throw new Error("Invalid OANDA Account ID format. Expected: 000-000-0000000-000");
                }
            }

            // 2. Duplicate Check
            const isDuplicate = accounts.some(acc => acc.account_number === accountNumber);
            if (isDuplicate) {
                throw new Error(`Account number ${accountNumber} is already added to this fund.`);
            }

            // Parse optional fields
            const supportedSymbols = supportedSymbolsInput.trim() 
                ? supportedSymbolsInput.split(',').map(s => s.trim()).filter(Boolean)
                : undefined;
            
            let riskSettings = undefined;
            if (riskSettingsInput.trim()) {
                try {
                    riskSettings = JSON.parse(riskSettingsInput);
                } catch {
                     throw new Error("Invalid JSON in Risk Settings");
                }
            }

            // Prepare Payload
            const cleanAccountNumber = accountNumber.trim();
            const cleanApiKey = apiKey.trim();
            const cleanAccountName = accountName.trim();

            const payload = {
                fund_id: fundId || undefined,
                broker_name: brokerName,
                account_name: cleanAccountName,
                account_number: cleanAccountNumber,
                is_live: isLive,
                credentials: {
                    api_key: cleanApiKey,
                    account_id: cleanAccountNumber, // Use accountNumber for OANDA ID
                    environment: isLive ? 'live' : 'practice'
                },
                supported_symbols: supportedSymbols,
                risk_settings: riskSettings
            };

            setPendingData(payload);
            setShowSaveConfirm(true);

        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to validate account";
            setError(message);
        }
    };

    const handleConfirmSave = async () => {
        if (!pendingData) return;
        setSubmitting(true);
        setError(null);
        
        try {
            await createAccount(pendingData);
            await fetchAccounts();
            setIsAdding(false);
            setSuccess("Account verified and saved successfully");
            // Reset form
            setAccountName('');
            setAccountNumber('');
            setApiKey('');
            setSupportedSymbolsInput('');
            setRiskSettingsInput('');
        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to save account";
            // If it's a backend validation error (like connection failed), it will show here
            setError(message);
        } finally {
            setSubmitting(false);
            setShowSaveConfirm(false);
            setPendingData(null);
        }
    };

    const confirmDelete = async () => {
        if (!deleteId) return;
        setIsDeleting(true);
        setError(null);
        setSuccess(null);
        
        try {
            await deleteAccount(deleteId);
            setAccounts(prev => prev.filter(a => a.id !== deleteId));
            setSuccess("Account deleted successfully");
        } catch (_err) {
            setError("Failed to delete account");
        } finally {
            setIsDeleting(false);
            setDeleteId(null);
        }
    };

    const handleFetchSymbols = async (accountId: string) => {
        setIsFetchingSymbols(true);
        try {
            const symbols = await fetchBrokerSymbols(accountId);
            setEditSymbols(prev => Array.from(new Set([...prev, ...symbols])));
            setSuccess(`Fetched ${symbols.length} symbols from broker`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to fetch symbols");
        } finally {
            setIsFetchingSymbols(false);
        }
    };

    const handleUpdate = async () => {
        if (!editingAccount) return;
        setSubmitting(true);
        setError(null);
        try {
            await updateAccount(editingAccount.id, {
                account_name: editingAccount.account_name,
                supported_symbols: editSymbols
            });
            await fetchAccounts();
            setEditingAccount(null);
            setSuccess("Account updated successfully");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update account");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            <ConfirmationModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={confirmDelete}
                title="Delete Account"
                message="Are you sure you want to remove this broker account? This action cannot be undone."
                confirmText="Delete"
                isLoading={isDeleting}
                variant="danger"
            />

            <ConfirmationModal
                isOpen={showSaveConfirm}
                onClose={() => setShowSaveConfirm(false)}
                onConfirm={handleConfirmSave}
                title="Confirm Account Connection"
                message={`Are you sure you want to connect ${brokerName} account ${pendingData?.account_number}? We will verify the credentials before saving.`}
                confirmText="Verify & Save"
                isLoading={submitting}
                variant="default"
            />
            
            {editingAccount && (
                 <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg w-full max-w-lg shadow-xl">
                        <h3 className="text-lg font-semibold text-white mb-4">Edit Account: {editingAccount.broker_name}</h3>
                        
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label>Account Alias</Label>
                                <Input 
                                    value={editingAccount.account_name}
                                    onChange={(e) => setEditingAccount({...editingAccount, account_name: e.target.value})}
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <Label>Supported Symbols</Label>
                                <div className="flex gap-2 mb-2">
                                    <Button 
                                        variant="outline" 
                                        size="sm" 
                                        onClick={() => handleFetchSymbols(editingAccount.id)}
                                        disabled={isFetchingSymbols}
                                        className="text-xs"
                                    >
                                        {isFetchingSymbols ? <Loader2 className="h-3 w-3 animate-spin mr-1"/> : <RefreshCw className="h-3 w-3 mr-1"/>}
                                        Fetch from Broker
                                    </Button>
                                </div>
                                <TagsInput 
                                    value={editSymbols}
                                    onChange={setEditSymbols}
                                    placeholder="Type symbol and press Enter..."
                                />
                                <p className="text-xs text-gray-500">
                                    Add symbols this account is allowed to trade. fetch from broker to auto-populate.
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end gap-2 mt-6">
                            <Button variant="ghost" onClick={() => setEditingAccount(null)}>Cancel</Button>
                            <Button onClick={handleUpdate} disabled={submitting}>
                                {submitting ? <Loader2 className="h-4 w-4 animate-spin"/> : "Save Changes"}
                            </Button>
                        </div>
                    </div>
                 </div>
            )}

            <Card className="bg-gray-950/50 backdrop-blur-sm border-gray-800">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Broker Accounts</CardTitle>
                        <CardDescription>Manage your connected trading accounts</CardDescription>
                    </div>
                    {!isAdding && (
                        <Button onClick={() => setIsAdding(true)} className="gap-2">
                            <Plus className="h-4 w-4" /> Add Account
                        </Button>
                    )}
                </CardHeader>
                <CardContent>
                    {error && (
                        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            {error}
                        </div>
                    )}
                    
                    {success && (
                        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-400 text-sm flex items-center gap-2">
                            <ShieldCheck className="h-4 w-4" />
                            {success}
                        </div>
                    )}

                    {isAdding && (
                        <form onSubmit={handleAdd} className="mb-6 p-4 border border-gray-800 rounded-lg bg-gray-900/50 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Broker</Label>
                                    <Select value={brokerName} onValueChange={setBrokerName}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="OANDA">OANDA</SelectItem>
                                            <SelectItem value="BINANCE">Binance (Coming Soon)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Account Alias</Label>
                                    <Input 
                                        placeholder="e.g. My Primary Oanda" 
                                        value={accountName}
                                        onChange={(e) => setAccountName(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Broker Account ID</Label>
                                    <Input 
                                        placeholder="e.g. 001-001-XXXXXXX-001" 
                                        value={accountNumber}
                                        onChange={(e) => setAccountNumber(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>API Key / Token</Label>
                                    <Input 
                                        type="password"
                                        placeholder="****************" 
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <input 
                                    type="checkbox" 
                                    id="isLive" 
                                    checked={isLive} 
                                    onChange={(e) => setIsLive(e.target.checked)}
                                    className="rounded border-gray-700 bg-gray-800"
                                />
                                <Label htmlFor="isLive">This is a Live Account</Label>
                            </div>
                            <div className="flex justify-end gap-2 mt-4">
                                <Button type="button" variant="ghost" onClick={() => setIsAdding(false)}>Cancel</Button>
                                <Button type="submit" disabled={submitting}>
                                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save Account"}
                                </Button>
                            </div>
                        </form>
                    )}

                    {loading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
                        </div>
                    ) : accounts.length === 0 && !isAdding ? (
                        <div className="text-center py-8 text-gray-500">
                            No broker accounts connected.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {accounts.map(acc => (
                                <div key={acc.id} className="flex items-center justify-between p-4 rounded-lg border border-gray-800 bg-gray-900/30 hover:border-gray-700 transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 font-bold text-xs">
                                            {acc.broker_name.substring(0, 2)}
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-gray-200">{acc.account_name}</h4>
                                            <div className="flex items-center gap-2 text-xs text-gray-500">
                                                <span>{acc.broker_name}</span>
                                                <span>•</span>
                                                <span className="font-mono">{acc.account_number || 'No Number'}</span>
                                                <span>•</span>
                                                <span className={`px-1.5 py-0.5 rounded ${acc.is_live ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                                                    {acc.is_live ? 'LIVE' : 'DEMO'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="flex items-center gap-1 text-xs text-green-500 bg-green-500/5 px-2 py-1 rounded border border-green-500/10">
                                            <ShieldCheck className="h-3 w-3" />
                                            Encrypted
                                        </div>
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-blue-400" onClick={() => {
                                            setEditingAccount(acc);
                                            setEditSymbols(acc.supported_symbols || []);
                                        }}>
                                            <Edit2 className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-red-400" onClick={() => setDeleteId(acc.id)}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </>
    );
}
