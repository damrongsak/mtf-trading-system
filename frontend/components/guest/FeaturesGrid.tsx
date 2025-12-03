'use client';

import { LineChart, BrainCircuit, TrendingUp } from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
}

const features: Feature[] = [
  {
    icon: <LineChart className="w-8 h-8" />,
    title: 'Multi-Timeframe Strategy',
    description: 'Macro bias from 4H/Daily timeframes, with precision entries on 15m charts. Combines Fibonacci retracements and SMC order blocks.',
    gradient: 'from-accent-green to-emerald-600',
  },
  {
    icon: <BrainCircuit className="w-8 h-8" />,
    title: 'AI Market Analyst',
    description: 'Google Gemini AI provides semantic market context and narrative-based reasoning for enhanced decision-making.',
    gradient: 'from-purple-500 to-purple-700',
  },
  {
    icon: <TrendingUp className="w-8 h-8" />,
    title: 'Smart Money Concepts',
    description: 'Identify institutional order blocks, liquidity zones, and market structure shifts for high-probability setups.',
    gradient: 'from-accent-blue to-blue-700',
  },
];

export function FeaturesGrid() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            Powerful Trading Features
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Advanced toolkit combining technical analysis, AI intelligence, and institutional trading concepts
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group relative p-8 rounded-2xl bg-gradient-to-br from-gray-800/40 to-gray-900/40 border border-gray-700/50 backdrop-blur-sm hover:border-gray-600 transition-all duration-300 hover:scale-105 hover:shadow-xl"
            >
              {/* Gradient Border Effect */}
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
              
              {/* Icon */}
              <div className={`inline-flex p-4 rounded-xl bg-gradient-to-br ${feature.gradient} mb-6 group-hover:scale-110 transition-transform duration-300`}>
                {feature.icon}
              </div>

              {/* Content */}
              <h3 className="text-2xl font-bold mb-4 text-white">
                {feature.title}
              </h3>
              <p className="text-gray-400 leading-relaxed">
                {feature.description}
              </p>

              {/* Hover Glow */}
              <div className={`absolute -inset-1 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300 -z-10`} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
