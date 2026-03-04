"use client";

import React from 'react';
import { ApiKeyManager } from '@/components/settings/ApiKeyManager';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function ApiKeysPage() {
    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-4">
                <Link 
                    href="/dashboard" 
                    className="p-2 bg-slate-800/50 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-full transition-colors"
                >
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-slate-100">Settings</h1>
                    <p className="text-slate-500">Manage your account and developer preferences.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-8">
                <section className="bg-slate-900/40 border border-slate-800/60 rounded-2xl p-8 backdrop-blur-sm">
                    <ApiKeyManager />
                </section>
                
                {/* Developer Information / Help */}
                <section className="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-8">
                    <h3 className="text-lg font-semibold text-blue-400 mb-4 flex items-center gap-2">
                        Developer Documentation
                    </h3>
                    <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                        MTF Olympus provides a high-performance REST API for external bots and custom integrations. 
                        Our API uses HMAC-SHA256 signatures for authentication to ensure maximum security for your funds.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                            <h4 className="text-slate-200 font-medium mb-1">HMAC Signature</h4>
                            <p className="text-xs text-slate-500">Sign your requests using your API Secret and a current timestamp.</p>
                        </div>
                        <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                            <h4 className="text-slate-200 font-medium mb-1">HFT-lite Endpoints</h4>
                            <p className="text-xs text-slate-500">Access direct Redis-backed snapshots for sub-10ms response times.</p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
