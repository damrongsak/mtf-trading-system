"use client";

import React, { useEffect, useState } from 'react';
import { defaultApi } from '@/lib/api/client';
import { APIResponseAgentList, Agent } from '@/lib/api/generated';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bot, Zap, Activity } from 'lucide-react';
import { toast } from 'sonner';

export function AgentList() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const response = await defaultApi.apiV1AiAgentsGet();
                if (response.data.data) {
                    setAgents(response.data.data);
                }
            } catch (error) {
                console.error("Failed to fetch agents", error);
                // toast.error("Failed to load agents"); // Optional: suppress on init if backend unstable
            } finally {
                setIsLoading(false);
            }
        };
        fetchAgents();
    }, []);

    if (isLoading) {
        return <div className="text-center p-4 text-muted-foreground">Loading agents...</div>;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
                <Card key={agent.id} className="relative overflow-hidden border-indigo-500/20 bg-indigo-950/10">
                    <div className="absolute top-0 right-0 p-2">
                        <Badge variant={agent.status === 'active' ? 'default' : 'secondary'} 
                               className={agent.status === 'active' ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' : ''}>
                            {agent.status}
                        </Badge>
                    </div>
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                                <Bot className="w-5 h-5 text-indigo-400" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">{agent.name}</CardTitle>
                                <CardDescription className="text-xs font-mono text-indigo-300">{agent.role}</CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground mb-4 min-h-[40px]">
                            {agent.description}
                        </p>
                        <div className="flex flex-wrap gap-1">
                            {agent.capabilities?.map((cap) => (
                                <Badge key={cap} variant="outline" className="text-[10px] border-indigo-500/20 text-indigo-300">
                                    <Zap className="w-3 h-3 mr-1" />
                                    {cap}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
