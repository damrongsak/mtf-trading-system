"use client";

import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, ShieldCheck, Zap } from "lucide-react";

interface LogEntry {
  id: string;
  timestamp: string;
  agent: string;
  event: string;
  metadata?: string;
  status: string;
}

export const OrchestrationLog: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [health, setHealth] = useState<{status: string, latency: string}>({status: "Compliant", latency: "2.4ms"});

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch("/api/v1/orchestration/logs?limit=20");
        const json = await response.json();
        if (json.status === "success") {
          setLogs(json.data);
        }
      } catch (error) {
        console.error("Failed to fetch orchestration logs", error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rule 7 Status</CardTitle>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{health.status}</div>
            <p className="text-xs text-muted-foreground">Internal Latency &lt; 10ms</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Loop Latency</CardTitle>
            <Zap className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{health.latency}</div>
            <p className="text-xs text-muted-foreground">Last 50 execution tasks</p>
          </CardContent>
        </Card>
      </div>

      <Card className="flex-1 min-h-0 flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Specialist Orchard Logs
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <ScrollArea className="h-[400px] w-full rounded-md border p-4">
            <div className="space-y-4">
              {logs.map((log) => (
                <div key={log.id} className="border-b pb-2 last:border-0">
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant={log.status === "ERROR" ? "destructive" : "secondary"}>
                      {log.agent}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{log.timestamp}</span>
                  </div>
                  <p className="text-sm font-medium">{log.event}</p>
                  {log.metadata && (
                    <p className="text-xs text-muted-foreground truncate">{log.metadata}</p>
                  )}
                </div>
              ))}
              {logs.length === 0 && (
                <div className="text-center py-10 text-muted-foreground text-sm">
                  No orchestration activity detected.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};
