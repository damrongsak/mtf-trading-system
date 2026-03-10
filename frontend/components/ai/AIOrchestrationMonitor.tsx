'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Zap, ShieldAlert, History, ArrowRightRight, BrainCircuit } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { OrchestrationApi, PipelineStatus } from '@/lib/api/generated';
import { format } from 'date-fns';
import axios from 'axios';

// Initialize API
const orchestrationApi = new OrchestrationApi();

export function AIOrchestrationMonitor() {
  const [logs, setLogs] = useState<any[]>([]);
  const [status, setStatus] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  const fetchOrchestrationData = async () => {
    try {
      const logsResp = await orchestrationApi.getOrchestrationLogs({ limit: 50 });
      const statusResp = await orchestrationApi.getPipelineStatus();
      
      setLogs(logsResp.data.data || []);
      setStatus(statusResp.data.data || {});
    } catch (err) {
      console.error("Failed to fetch orchestration logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrchestrationData();
    const interval = setInterval(fetchOrchestrationData, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, []);

  const getLogIcon = (type: string) => {
    switch (type) {
      case 'agent_handoff': return <ArrowRightRight className="h-3 w-3 text-indigo-400" />;
      case 'pipeline_execution': return <Zap className="h-3 w-3 text-amber-400" />;
      case 'risk_audit': return <ShieldAlert className="h-3 w-3 text-red-400" />;
      default: return <Activity className="h-3 w-3 text-gray-400" />;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'STARTED': return <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-400">STARTED</Badge>;
      case 'COMPLETED': return <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-400">COMPLETED</Badge>;
      case 'FAILED': return <Badge variant="outline" className="text-[10px] border-red-500/30 text-red-400">FAILED</Badge>;
      case 'TRUE': return <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400">TRIGGERED</Badge>;
      case 'FALSE': return <Badge variant="outline" className="text-[10px] border-gray-500/30 text-gray-400">SKIPPED</Badge>;
      default: return <Badge variant="outline" className="text-[10px] border-gray-500/30 text-gray-400">{status}</Badge>;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Active Pipelines */}
      <Card className="lg:col-span-1 border-gray-800 bg-gray-950/40">
        <CardHeader className="py-4 border-b border-gray-800/50">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-indigo-400" />
            Autonomous Pipelines
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 space-y-4">
          {Object.entries(status).map(([key, pipeline]: [string, any]) => (
            <div key={key} className="p-3 rounded-lg bg-gray-900/50 border border-gray-800 space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="text-xs font-semibold text-gray-200 capitalize">
                  {key.replace(/_/g, ' ')}
                </h4>
                <Badge className={pipeline.status === 'ACTIVE' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}>
                  {pipeline.status}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-400 mt-2">
                <div>
                  <span className="block opacity-60">Last Run</span>
                  <span className="text-gray-300">
                    {pipeline.last_run !== 'Never' ? format(new Date(pipeline.last_run), 'HH:mm:ss') : 'Never'}
                  </span>
                </div>
                <div>
                  <span className="block opacity-60">Symbol</span>
                  <span className="text-gray-300 font-mono">{pipeline.monitored_symbol}</span>
                </div>
                <div>
                  <span className="block opacity-60">Ref. Score</span>
                  <span className="text-gray-300 font-mono">{pipeline.current_reference_score?.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))}
          {Object.keys(status).length === 0 && (
             <p className="text-xs text-center text-gray-500 py-6 italic">No active pipelines found.</p>
          )}
        </CardContent>
      </Card>

      {/* Audit Logs */}
      <Card className="lg:col-span-2 border-gray-800 bg-gray-950/40">
        <CardHeader className="py-4 border-b border-gray-800/50 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <History className="h-4 w-4 text-purple-400" />
            Orchestration Audit Trail
          </CardTitle>
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Real-time Feed</span>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[400px]">
            <div className="divide-y divide-gray-800/50">
              {logs.map((log) => (
                <div key={log.id} className="p-3 hover:bg-gray-800/20 transition-colors">
                  <div className="flex items-start gap-4">
                    <div className="mt-1 p-1.5 rounded bg-gray-900 border border-gray-800">
                      {getLogIcon(log.type)}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] font-bold text-gray-300 flex items-center gap-1.5">
                          {log.source_agent && (
                             <>
                               {log.source_agent}
                               <ArrowRightRight className="h-2 w-2 opacity-40" />
                               {log.target_agent}
                             </>
                          )}
                          {!log.source_agent && log.pipeline}
                        </span>
                        <span className="text-[10px] text-gray-500 font-mono font-medium">
                          {format(new Date(log.timestamp), 'HH:mm:ss')}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                         {getStatusBadge(log.status || log.triggered)}
                         <p className="text-[10px] text-gray-400 leading-relaxed truncate max-w-[400px]">
                            {log.query || log.error || (log.drift ? `Drift detected: ${log.drift}` : "Log entry")}
                         </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              {logs.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center py-20 opacity-50 space-y-3">
                   <Activity className="h-10 w-10 text-gray-600 animate-pulse" />
                   <p className="text-sm text-gray-500">Awaiting system events...</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
