'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ExecutionBrokerAccount, getBrokerAccounts } from '@/lib/api/execution';
import { logger } from '@/lib/api/app-logger';

interface AccountContextType {
    accounts: ExecutionBrokerAccount[];
    selectedAccount: ExecutionBrokerAccount | null;
    selectAccount: (accountId: string) => void;
    isLoading: boolean;
    isLive: boolean;
}

const AccountContext = createContext<AccountContextType | undefined>(undefined);

export function AccountProvider({ children }: { children: ReactNode }) {
    const [accounts, setAccounts] = useState<ExecutionBrokerAccount[]>([]);
    const [selectedAccount, setSelectedAccount] = useState<ExecutionBrokerAccount | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        async function loadAccounts() {
            try {
                const data = await getBrokerAccounts();
                setAccounts(data);
                
                // Restore selection or default to first
                const storedId = localStorage.getItem('selected_broker_account_id');
                let found = null;
                
                if (storedId) {
                    found = data.find(a => a.id === storedId);
                }
                
                if (!found && data.length > 0) {
                    found = data[0];
                }
                
                if (found) {
                    setSelectedAccount(found);
                    // Persist if fallback was used
                    localStorage.setItem('selected_broker_account_id', found.id);
                }
            } catch (err) {
                logger.error("Failed to load broker accounts", err);
            } finally {
                setIsLoading(false);
            }
        }
        loadAccounts();
    }, []);

    const selectAccount = (accountId: string) => {
        const found = accounts.find(a => a.id === accountId);
        if (found) {
            setSelectedAccount(found);
            localStorage.setItem('selected_broker_account_id', found.id);
        }
    };

    const isLive = selectedAccount?.environment === 'live';

    return (
        <AccountContext.Provider value={{ accounts, selectedAccount, selectAccount, isLoading, isLive }}>
            {children}
        </AccountContext.Provider>
    );
}

export function useAccount() {
    const context = useContext(AccountContext);
    if (context === undefined) {
        throw new Error('useAccount must be used within an AccountProvider');
    }
    return context;
}
