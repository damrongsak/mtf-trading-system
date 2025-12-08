'use client';

import React from 'react';
import { AIAnalystCard } from '@/components/ai/AIAnalystCard';
import { Bot, TrendingUp, Brain, Zap } from 'lucide-react';

export default function AIAnalystPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
          <Bot className="w-8 h-8 text-indigo-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            AI Market Analyst
          </h1>
          <p className="text-gray-400 mt-1">
            Get AI-powered insights on market trends and trading opportunities
          </p>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-gradient-to-br from-blue-950/20 to-indigo-950/20 border border-blue-500/30">
          <TrendingUp className="w-6 h-6 text-blue-400 mb-2" />
          <h3 className="font-semibold text-blue-100 mb-1">Trend Analysis</h3>
          <p className="text-sm text-gray-400">
            Real-time market trend identification across multiple timeframes
          </p>
        </div>
        
        <div className="p-4 rounded-lg bg-gradient-to-br from-purple-950/20 to-pink-950/20 border border-purple-500/30">
          <Brain className="w-6 h-6 text-purple-400 mb-2" />
          <h3 className="font-semibold text-purple-100 mb-1">Smart Insights</h3>
          <p className="text-sm text-gray-400">
            AI-driven analysis of key levels and trading signals
          </p>
        </div>
        
        <div className="p-4 rounded-lg bg-gradient-to-br from-indigo-950/20 to-violet-950/20 border border-indigo-500/30">
          <Zap className="w-6 h-6 text-indigo-400 mb-2" />
          <h3 className="font-semibold text-indigo-100 mb-1">Instant Updates</h3>
          <p className="text-sm text-gray-400">
            Get fresh market analysis on-demand with a single click
          </p>
        </div>
      </div>

      {/* Main AI Analyst Card */}
      <AIAnalystCard />

      {/* Information Section */}
      <div className="p-6 rounded-lg bg-gradient-to-br from-slate-900/50 to-gray-900/50 border border-gray-700/50">
        <h2 className="text-xl font-semibold text-gray-200 mb-3">How It Works</h2>
        <div className="space-y-2 text-gray-400">
          <p>
            Our AI Market Analyst uses advanced language models to analyze current market conditions,
            technical indicators, and recent price action to provide actionable insights.
          </p>
          <p>
            The analysis considers:
          </p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Multi-timeframe trend analysis (4H, 1H, 15M)</li>
            <li>Key support and resistance levels</li>
            <li>Recent candlestick patterns and signals</li>
            <li>Market structure and Smart Money Concepts</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
