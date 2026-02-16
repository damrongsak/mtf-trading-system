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

    // Initial fetch on mount
    useEffect(() => {
        fetchBriefing();
    }, []);

    return (
        <Card className="flex flex-col min-h-[400px] max-h-[600px] bg-gray-950/40 backdrop-blur-xl border-amber-500/20 hover:border-amber-500/40 transition-all duration-500 shadow-2xl shadow-amber-900/5 overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between py-4 px-6 border-b border-white/5 bg-gradient-to-r from-amber-500/10 via-transparent to-transparent">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-lg">
                        <Sunrise className="h-5 w-5 text-amber-500" />
                    </div>
                    <div>
                        <CardTitle className="text-lg font-bold tracking-tight text-amber-500">
                            Morning Briefing
                        </CardTitle>
                        <p className="text-[10px] text-gray-500 font-medium tracking-widest uppercase">
                            Institutional Signal Summary
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    {lastUpdated && (
                        <span className="text-[10px] font-mono text-gray-500 hidden sm:inline bg-white/5 px-2 py-1 rounded">
                            LATEST: {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-9 w-9 p-0 hover:bg-amber-500/10 hover:text-amber-400 border border-white/5 rounded-full"
                        onClick={fetchBriefing}
                        disabled={loading}
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="flex-1 overflow-hidden p-0 relative flex flex-col">
                <div className="flex-1 overflow-y-auto p-8 scrollbar-thin scrollbar-thumb-amber-500/20 scrollbar-track-transparent">
                    {loading && !content && (
                        <div className="flex flex-col items-center justify-center h-full space-y-6 text-gray-400">
                            <div className="relative">
                                <div className="w-16 h-16 border-2 border-gray-800 rounded-full"></div>
                                <div className="w-16 h-16 border-t-2 border-amber-500 rounded-full animate-spin absolute top-0"></div>
                                <Sunrise className="h-6 w-6 text-amber-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                            </div>
                            <div className="text-center space-y-1">
                                <p className="text-sm font-medium text-amber-200">Synthesizing Market Intelligence</p>
                                <p className="text-[10px] text-gray-500 italic">"The Weaver is pattern-matching H4/D1 structures..."</p>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-4">
                            <div className="p-4 bg-red-500/10 rounded-full">
                                <AlertCircle className="h-10 w-10 opacity-50" />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-semibold">{error}</p>
                                <p className="text-xs text-red-400/60 mt-1">Check AI Analyst service status</p>
                            </div>
                            <Button variant="outline" size="sm" onClick={fetchBriefing} className="mt-2 border-red-500/20 bg-red-500/5 hover:bg-red-500/20 text-red-400">
                                Retry Connection
                            </Button>
                        </div>
                    )}

                    {content && !loading && (
                        <div className="prose prose-invert prose-sm max-w-none 
                            prose-headings:text-amber-100 prose-headings:font-bold prose-headings:tracking-tight prose-headings:mt-8 prose-headings:mb-4
                            prose-h1:text-2xl prose-h1:border-b prose-h1:border-amber-500/20 prose-h1:pb-2
                            prose-h2:text-xl prose-h2:text-amber-400/90
                            prose-h3:text-lg prose-h3:text-amber-500/80
                            prose-p:text-gray-300 prose-p:leading-relaxed prose-p:mb-4
                            prose-strong:text-amber-400 prose-strong:font-semibold
                            prose-ul:text-gray-300 prose-ul:my-4 prose-li:mb-2
                            prose-li:marker:text-amber-500/50
                            prose-code:text-amber-200 prose-code:bg-amber-500/10 prose-code:px-1 prose-code:rounded
                        ">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {content}
                            </ReactMarkdown>
                        </div>
                    )}
                    
                    {/* Overlay loading state when refreshing with existing content */}
                    {loading && content && (
                         <div className="absolute inset-0 bg-gray-950/40 flex items-center justify-center z-10 backdrop-blur-sm transition-all duration-300">
                              <div className="bg-gray-900/80 p-4 rounded-2xl border border-amber-500/30 shadow-2xl">
                                <RefreshCw className="h-8 w-8 text-amber-500 animate-spin" />
                              </div>
                         </div>
                    )}
                </div>
            </CardContent>
            
             <CardFooter className="py-3 px-6 border-t border-white/5 bg-gray-900/40 text-[10px] text-gray-400 flex justify-between items-center">
                <div className="flex items-center gap-2 opacity-60">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                    <span>AI Engine Active (Gemini 2.5)</span>
                </div>
                <div className="flex items-center gap-3 opacity-60 tracking-wider uppercase font-medium">
                    <span className="flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        v2.1 SDD
                    </span>
                </div>
            </CardFooter>
        </Card>
    );
}
    );
}
