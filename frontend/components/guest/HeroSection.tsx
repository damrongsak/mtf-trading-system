'use client';

import Link from 'next/link';
import { ArrowRight, TrendingUp } from 'lucide-react';

export function HeroSection() {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950" />
        <div className="absolute inset-0 bg-[url('/hero-pattern.svg')] opacity-5" />
        
        {/* Gradient Orbs */}
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-accent-blue/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
        {/* Trust Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm mb-8 animate-fade-in">
          <TrendingUp className="w-4 h-4 text-accent-green" />
          <span className="text-sm text-gray-300">
            AI-Powered • Real-time Analysis • $10 Risk Management
          </span>
        </div>

        {/* Main Headline */}
        <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white via-gray-200 to-gray-400 leading-tight animate-slide-up">
          Intelligent XAU/USD Trading
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent-blue via-purple-400 to-accent-blue bg-size-200 animate-gradient">
            with Multi-Timeframe Analysis
          </span>
        </h1>

        {/* Subheadline */}
        <p className="text-xl md:text-2xl text-gray-400 mb-12 max-w-3xl mx-auto animate-slide-up delay-100">
          Combine Smart Money Concepts with AI-powered market insights for precision Gold trading
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-slide-up delay-200">
          <Link
            href="/login"
            className="group px-8 py-4 bg-gradient-to-r from-accent-blue to-purple-600 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-accent-blue/50 transition-all duration-300 hover:scale-105 flex items-center gap-2"
          >
            Start Trading
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          
          <Link
            href="#signals-preview"
            className="px-8 py-4 bg-gray-800/50 border border-gray-700 text-white rounded-lg font-semibold hover:bg-gray-700/50 transition-all duration-300 backdrop-blur-sm"
          >
            View Live Signals
          </Link>
        </div>

        {/* Stats Preview */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto animate-fade-in delay-300">
          {[
            { label: 'Win Rate', value: '68.5%' },
            { label: 'Avg R:R', value: '2.8:1' },
            { label: 'Trades/Month', value: '142' },
            { label: 'Active Signals', value: '12' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white mb-1">
                {stat.value}
              </div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 border-2 border-gray-700 rounded-full flex justify-center pt-2">
          <div className="w-1.5 h-3 bg-gray-600 rounded-full animate-scroll" />
        </div>
      </div>
    </section>
  );
}
