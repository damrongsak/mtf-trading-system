'use client';

import { ShieldCheck, BrainCircuit, Activity, Zap, Layers } from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
}

const features: Feature[] = [
  {
    icon: <Layers className="w-8 h-8" />,
    title: 'The Strategy Foundry',
    description: 'Stop writing spaghetti code. Snap together standardized logic blocks like "Trend Following" and "Mean Reversion" to build robust strategies.',
    gradient: 'from-blue-500 to-indigo-600',
  },
  {
    icon: <ShieldCheck className="w-8 h-8" />,
    title: 'The Proving Ground',
    description: 'Rigorous Walk-Forward Validation. Use a "Train/Test" gauntlet to identify and kill overfitted strategies before they risk your capital.',
    gradient: 'from-accent-green to-emerald-600',
  },
  {
    icon: <Activity className="w-8 h-8" />,
    title: 'The Risk Citadel',
    description: 'Game Theoretic Risk Management. Minimax Regret and Portfolio Risk Parity ensure you survive volatility and avoid "Gambler\'s Ruin".',
    gradient: 'from-orange-500 to-red-600',
  },
  {
    icon: <Zap className="w-8 h-8" />,
    title: 'The Execution Edge',
    description: 'Professional-grade Smart Order Routing and liquidity analysis to get the best fills and minimize slippage.',
    gradient: 'from-yellow-400 to-orange-500',
  },
  {
    icon: <BrainCircuit className="w-8 h-8" />,
    title: 'The AI Coach',
    description: 'Your digital mentor. Detects "Tilt" and "C-Game" patterns in your behavior and intervenes with Mental Hand History exercises.',
    gradient: 'from-purple-500 to-purple-700',
  },
];

export function FeaturesGrid() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            The 5 Pillars of Olympus
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            A complete ecosystem designed to turn retail traders into Fund Managers
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 justify-center">
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
