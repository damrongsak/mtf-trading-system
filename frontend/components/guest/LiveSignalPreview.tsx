'use client';

import { demoSignals } from '@/lib/demo-data';
import { ArrowUp, ArrowDown, Clock, TrendingUp } from 'lucide-react';

export function LiveSignalPreview() {
  return (
    <section id="signals-preview" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-green/10 border border-accent-green/20 mb-4">
            <div className="w-2 h-2 bg-accent-green rounded-full animate-pulse" />
            <span className="text-sm text-accent-green font-medium">LIVE SIGNALS</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            Recent Trading Signals
          </h2>
          <p className="text-xl text-gray-400">
            See our AI-powered signals in action
          </p>
        </div>

        {/* Signals Grid */}
        <div className="grid md:grid-cols-3 gap-6">
          {demoSignals.map((signal, index) => (
            <div
              key={signal.id}
              className="relative group animate-fade-in"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Glassmorphism Card */}
              <div className="relative p-6 rounded-2xl bg-gradient-to-br from-gray-800/60 to-gray-900/60 border border-gray-700/50 backdrop-blur-md hover:border-gray-600 transition-all duration-300 hover:scale-105">
                {/* Direction Badge */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-500">{signal.timeframe}</span>
                  <div
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold text-sm ${
                      signal.direction === 'BULLISH'
                        ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                        : 'bg-accent-red/20 text-accent-red border border-accent-red/30'
                    }`}
                  >
                    {signal.direction === 'BULLISH' ? (
                      <ArrowUp className="w-4 h-4" />
                    ) : (
                      <ArrowDown className="w-4 h-4" />
                    )}
                    {signal.direction}
                  </div>
                </div>

                {/* Symbol */}
                <h3 className="text-2xl font-bold text-white mb-3">
                  {signal.symbol}
                </h3>

                {/* Setup Info */}
                <p className="text-gray-400 text-sm mb-4">
                  {signal.setup}
                </p>

                {/* Confidence Bar */}
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs text-gray-500">Confidence</span>
                    <span className="text-sm font-bold text-white">{signal.confidence}%</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${
                        signal.direction === 'BULLISH'
                          ? 'bg-gradient-to-r from-accent-green to-emerald-400'
                          : 'bg-gradient-to-r from-accent-red to-red-400'
                      }`}
                      style={{ width: `${signal.confidence}%` }}
                    />
                  </div>
                </div>

                {/* Timestamp */}
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  {signal.timestamp}
                </div>

                {/* Hover Glow Effect */}
                <div className={`absolute -inset-1 rounded-2xl opacity-0 group-hover:opacity-30 blur-xl transition-opacity duration-300 -z-10 ${
                  signal.direction === 'BULLISH'
                    ? 'bg-accent-green'
                    : 'bg-accent-red'
                }`} />
              </div>

              {/* Blur Overlay for Demo */}
              <div className="absolute inset-0 backdrop-blur-[2px] rounded-2xl flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="px-6 py-3 bg-gray-900/90 rounded-lg border border-accent-blue/50 backdrop-blur-sm">
                  <p className="text-sm font-semibold text-accent-blue flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Sign up to unlock full details
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <a
            href="/login"
            className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-accent-blue to-purple-600 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-accent-blue/50 transition-all duration-300 hover:scale-105"
          >
            Get Full Access
            <ArrowUp className="w-5 h-5" />
          </a>
        </div>
      </div>
    </section>
  );
}
