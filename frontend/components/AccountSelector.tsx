'use client';

import React from 'react';
import { useAccount } from '@/context/AccountContext';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

export function AccountSelector() {
    const { accounts, selectedAccount, selectAccount, isLoading } = useAccount();

    if (isLoading) {
        return <div className="text-sm text-muted-foreground">Loading accounts...</div>;
    }

    if (accounts.length === 0) {
        return <div className="text-sm text-yellow-500">No Broker Accounts</div>;
    }

    return (
        <div className="flex items-center space-x-2">
            <Select 
                value={selectedAccount?.id} 
                onValueChange={(value) => selectAccount(value)}
            >
                <SelectTrigger className="w-[240px] h-9">
                    <SelectValue placeholder="Select Account" />
                </SelectTrigger>
                <SelectContent>
                    {accounts.map((account) => (
                        <SelectItem key={account.id} value={account.id}>
                            <div className="flex items-center justify-between w-full gap-2">
                                <span className="font-medium">{account.broker_name}</span>
                                <span className="text-xs text-muted-foreground px-2">
                                    {account.account_id}
                                </span>
                                {account.environment === 'live' ? (
                                    <Badge variant="destructive" className="h-5 px-1 text-[10px] uppercase">
                                        Live
                                    </Badge>
                                ) : (
                                    <Badge variant="secondary" className="h-5 px-1 text-[10px] uppercase bg-green-900/20 text-green-400">
                                        Demo
                                    </Badge>
                                )}
                            </div>
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}
