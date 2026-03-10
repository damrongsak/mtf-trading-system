'use client';

import React from 'react';
import { AIAnalystCard } from '@/components/ai/AIAnalystCard';
import { AIOrchestrationMonitor } from '@/components/ai/AIOrchestrationMonitor';
import { Bot, TrendingUp, Brain, Zap, Activity } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function AIAnalystPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
            <Bot className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              AI Analyst & Orchestrator
            </h1>
            <p className="text-gray-400 mt-1">
              Advanced market reasoning and autonomous agent monitoring
            </p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="advisor" className="space-y-6">
        <TabsList className="bg-gray-900/50 border border-gray-800 p-1 h-12">
          <TabsTrigger value="advisor" className="gap-2 px-6 h-10 data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-300 transition-all">
            <Brain className="w-4 h-4" />
            Strategy Advisor
          </TabsTrigger>
          <TabsTrigger value="monitor" className="gap-2 px-6 h-10 data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300 transition-all">
            <Activity className="w-4 h-4" />
            Orchestration Monitor
          </TabsTrigger>
        </TabsList>

        <TabsContent value="advisor" className="space-y-6 mt-0">
          {/* Feature Cards (Slim) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-gradient-to-br from-blue-950/20 to-indigo-950/20 border border-blue-500/30">
              <TrendingUp className="w-6 h-6 text-blue-400 mb-2" />
              <h3 className="font-semibold text-blue-100 mb-1">Concept Reasoning</h3>
              <p className="text-sm text-gray-400">
                Multi-agent Smarts with built-in SMC logic
              </p>
            </div>
            
            <div className="p-4 rounded-lg bg-gradient-to-br from-purple-950/20 to-pink-950/20 border border-purple-500/30">
              <Brain className="w-6 h-6 text-purple-400 mb-2" />
              <h3 className="font-semibold text-purple-100 mb-1">Strategy Advisor</h3>
              <p className="text-sm text-gray-400">
                Backtest-validated logic proposals (vectorbt)
              </p>
            </div>
            
            <div className="p-4 rounded-lg bg-gradient-to-br from-indigo-950/20 to-violet-950/20 border border-indigo-500/30">
              <Zap className="w-6 h-6 text-indigo-400 mb-2" />
              <h3 className="font-semibold text-indigo-100 mb-1">Handoff Protocol</h3>
              <p className="text-sm text-gray-400">
                Autonomous specialist agent consultation
              </p>
            </div>
          </div>

          <AIAnalystCard />
        </TabsContent>

        <TabsContent value="monitor" className="mt-0">
          <AIOrchestrationMonitor />
        </TabsContent>
      </Tabs>

      {/* Information Section */}
      <div className="p-6 rounded-lg bg-gradient-to-br from-slate-900/50 to-gray-900/50 border border-gray-700/50">
        <h2 className="text-xl font-semibold text-gray-200 mb-3">Phase 4: Autonomous Workflows</h2>
        <div className="space-y-2 text-gray-400 text-sm">
          <p>
            MTF Olympus v2.5 introduces <strong>Autonomous Agentic Orchestration</strong>. 
            The Strategy Advisor now automatically triggers specialist handoffs and 
            backtest loops (via vectorbt) before finalizing trade logic modifications.
          </p>
          <p>
            Key Capabilities:
          </p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li><strong>Sentiment-to-Risk Pipeline</strong>: Proactive drift detection in Gold sentiment.</li>
            <li><strong>Strategy Backtest Loop</strong>: Automatic validation of logic changes.</li>
            <li><strong>Agent Handoffs</strong>: Specialized consultation for cross-domain tasks.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
