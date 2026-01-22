'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Sunrise, AlertCircle, FileText } from "lucide-react";
import { aiApi } from "@/lib/api/ai";
import ReactMarkdown from "react-markdown";
import remarkGfm from 'remark-gfm';
import { cn } from "@/lib/utils";
import { logger } from "@/lib/api/app-logger";

export function DailyBriefingWidget() {
    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const fetchBriefing = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await aiApi.getDailyBriefing();
            setContent(data.content);
            setLastUpdated(new Date());
        } catch (err: any) {
            logger.error("Failed to fetch briefing:", err);
            setError(err.message || "Failed to load briefing");
        } finally {
            setLoading(false);
        }
    };

    // Initial fetch on mount if no content? Or wait for user?
    // Let's auto-fetch on mount for convenience
    useEffect(() => {
        fetchBriefing();
    }, []);

    return (
        <Card className="col-span-1 md:col-span-2 lg:col-span-3 flex flex-col h-[500px] bg-gray-950 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b border-gray-800 bg-gray-900/50">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-amber-500">
                    <Sunrise className="h-4 w-4" />
                    Morning Briefing
                </CardTitle>
                <div className="flex items-center gap-2">
                    {lastUpdated && (
                        <span className="text-[10px] text-gray-500 hidden sm:inline">
                            Updated: {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 hover:text-amber-400"
                        onClick={fetchBriefing}
                        disabled={loading}
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="flex-1 overflow-hidden p-0 relative flex flex-col">
                <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                    {loading && !content && (
                        <div className="flex flex-col items-center justify-center h-full space-y-4 text-gray-500">
                            <div className="relative">
                                <div className="w-12 h-12 border-4 border-gray-800 rounded-full"></div>
                                <div className="w-12 h-12 border-4 border-amber-500 rounded-full animate-spin absolute top-0 border-t-transparent"></div>
                            </div>
                            <p className="text-xs animate-pulse">Consulting the Weaver...</p>
                        </div>
                    )}

                    {error && (
                        <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-2">
                            <AlertCircle className="h-8 w-8 opacity-50" />
                            <p className="text-sm">{error}</p>
                            <Button variant="outline" size="sm" onClick={fetchBriefing} className="mt-2 border-red-900 bg-red-950/30 hover:bg-red-900/50">
                                Retry
                            </Button>
                        </div>
                    )}

                    {content && !loading && (
                        <div className="prose prose-invert prose-sm max-w-none 
                            prose-headings:text-amber-100 prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                            prose-p:text-gray-300 prose-p:leading-relaxed
                            prose-strong:text-amber-400
                            prose-ul:text-gray-300 prose-li:marker:text-gray-600
                        ">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {content}
                            </ReactMarkdown>
                        </div>
                    )}
                    
                    {/* Overlay loading state when refreshing with existing content */}
                    {loading && content && (
                         <div className="absolute inset-0 bg-gray-950/60 flex items-center justify-center z-10 backdrop-blur-[1px]">
                              <RefreshCw className="h-8 w-8 text-amber-500 animate-spin opacity-80" />
                         </div>
                    )}
                </div>
            </CardContent>
            
             <CardFooter className="py-2 px-4 border-t border-gray-800 bg-gray-900/30 text-[10px] text-gray-500 flex justify-between">
                <span>AI-Generated • Verify independently</span>
                <span className="flex items-center gap-1 opacity-70">
                    <FileText className="h-3 w-3" />
                    v2.0 Pre-Flight
                </span>
            </CardFooter>
        </Card>
    );
}
