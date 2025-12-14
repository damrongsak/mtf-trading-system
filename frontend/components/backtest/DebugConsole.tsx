import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LogEntry {
    timestamp: Date;
    message: string;
    type: 'info' | 'error' | 'success' | 'warning';
}

interface DebugConsoleProps {
    logs: LogEntry[];
    className?: string;
}

export function DebugConsole({ logs, className }: DebugConsoleProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <Card className={cn("border-border/50 bg-black/90 font-mono text-xs", className)}>
            <CardHeader className="py-3 px-4 border-b border-white/10">
                <CardTitle className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Terminal className="w-4 h-4" />
                    Console Output
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <div 
                    ref={scrollRef}
                    className="h-[200px] overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-white/10"
                >
                    {logs.length === 0 && (
                        <div className="text-muted-foreground italic opacity-50">
                            Ready...
                        </div>
                    )}
                    {logs.map((log, idx) => (
                        <div key={idx} className="flex gap-2">
                            <span className="text-muted-foreground opacity-50 shrink-0">
                                [{log.timestamp.toLocaleTimeString()}]
                            </span>
                            <span className={cn(
                                "break-all",
                                log.type === 'error' && "text-red-400",
                                log.type === 'success' && "text-green-400",
                                log.type === 'warning' && "text-yellow-400",
                                log.type === 'info' && "text-zinc-300"
                            )}>
                                {log.message}
                            </span>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
