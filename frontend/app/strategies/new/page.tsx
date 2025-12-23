
'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { strategiesApi } from '@/lib/api/strategies';
import { LogicTemplate } from '@/lib/api/types';
import Link from 'next/link';

export default function NewStrategyPage() {
    const router = useRouter();
    const [templates, setTemplates] = useState<LogicTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadTemplates() {
            try {
                const response = await strategiesApi.getTemplates();
                // Response is APIResponse<LogicTemplate[]> or just LogicTemplate[]?
                // strategiesApi.getTemplates() returns response.data which is APIResponse<T[]>['data'] ?
                // Checking strategies.ts: returns response.data. 
                // Wait, response.data in axios is the body. The body is APIResponse.
                // So strategiesApi.getTemplates -> returns APIResponse.
                // I need to check how I implemented the API Client for getTemplates.
                // In strategies.ts: return response.data.
                // If the backend returns {status:..., data: [...]}, then response.data IS that object.
                // So I need to access .data from it.
                // But my client helper usually unwraps? 
                // Let's assume strategiesApi returns the full APIResponse object based on my code.
                // "return response.data" in axios returns the body.
                // So `const result = await ...` -> result.data is the array.
                
                const result = await strategiesApi.getTemplates();
                if (result.status === 'success' && Array.isArray(result.data)) {
                    setTemplates(result.data);
                } else {
                    setError('Failed to load templates or invalid format');
                }
            } catch (err) {
                setError('Error loading templates');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        loadTemplates();
    }, []);

    if (loading) {
        return <div className="p-8 text-center text-gray-400">Loading templates...</div>;
    }

    if (error) {
        return <div className="p-8 text-center text-red-400">{error}</div>;
    }

    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-100">Create New Strategy</h1>
                    <p className="text-gray-400 mt-2">Select a strategy template to get started</p>
                </div>
                <Link href="/strategies" className="text-gray-400 hover:text-white transition-colors">
                    Cancel
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {templates.map((template) => (
                    <div 
                        key={template.id} 
                        className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 hover:border-accent-blue/50 transition-all duration-300 group flex flex-col"
                    >
                        <div className="mb-4">
                            <div className="h-12 w-12 bg-accent-blue/10 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <svg className="w-6 h-6 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-bold text-gray-100 mb-2">{template.name}</h3>
                            <p className="text-gray-400 text-sm leading-relaxed mb-4">
                                {template.description}
                            </p>
                            
                            <div className="flex flex-wrap gap-2 mb-4">
                                {Object.keys(template.default_config || {}).slice(0, 3).map(key => (
                                    <span key={key} className="text-xs px-2 py-1 bg-gray-800 rounded text-gray-300 font-mono">
                                        {key}
                                    </span>
                                ))}
                                {Object.keys(template.default_config || {}).length > 3 && (
                                    <span className="text-xs px-2 py-1 bg-gray-800 rounded text-gray-500">...</span>
                                )}
                            </div>
                        </div>

                        <div className="mt-auto pt-6 border-t border-gray-800">
                             <Link
                                href={`/strategies/configure/${template.id}`}
                                className="block w-full text-center py-3 bg-accent-blue hover:bg-accent-blue/90 text-white rounded-lg font-medium transition-colors"
                            >
                                Select Template
                            </Link>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
