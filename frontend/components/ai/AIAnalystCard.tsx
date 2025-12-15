'use client';

import React, { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Brain, RefreshCw, AlertTriangle } from "lucide-react";
import { useAIAnalyst } from "@/lib/hooks/useAIAnalyst";
import ReactMarkdown from "react-markdown";

export function AIAnalystCard() {
  const { report, timestamp, loading, error, generateReport } = useAIAnalyst();

  // Auto-fetch on mount
  useEffect(() => {
    generateReport();
  }, []);

  return (
    <Card className="col-span-1 md:col-span-2 lg:col-span-3">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-500" />
          AI Market Observer
        </CardTitle>
        <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0" 
            onClick={() => generateReport()}
            disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
            <div className="flex items-center gap-2 text-red-500 text-sm p-4 bg-red-50/10 rounded-md">
                <AlertTriangle className="h-4 w-4" />
                <span>{error}</span>
            </div>
        ) : (
            <div className="space-y-4">
                <div className="text-xs text-muted-foreground flex justify-between">
                    <span>Latest Situation Report</span>
                    <span>{timestamp || "Waiting for analysis..."}</span>
                </div>
                
                <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 min-h-[150px] text-sm leading-relaxed prose prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1">
                    {loading && !report ? (
                        <div className="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground">
                            <RefreshCw className="h-6 w-6 animate-spin" />
                            <span>Analyzing market conditions...</span>
                        </div>
                    ) : (
                        <ReactMarkdown>{report || "Click refresh to generate a market report."}</ReactMarkdown>
                    )}
                </div>
            </div>
        )}
      </CardContent>
    </Card>
  );
}
