'use client';

import { Search, Target, Zap } from 'lucide-react';

const steps = [
  {
    number: '01',
    icon: <Search className="w-8 h-8" />,
    title: 'Analysis',
    description: 'AI scans 4H/Daily trends combined with real-time news sentiment',
    color: 'accent-blue',
  },
  {
    number: '02',
    icon: <Target className="w-8 h-8" />,
    title: 'Setup',
    description: 'Detects Fibonacci zones and SMC order blocks for optimal entries',
    color: 'purple-500',
  },
  {
    number: '03',
    icon: <Zap className="w-8 h-8" />,
    title: 'Execute',
    description: '15m trigger signals delivered with strict $10 max risk management',
    color: 'accent-green',
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 px-6 bg-gradient-to-b from-gray-950 to-gray-900">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            How It Works
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Three simple steps to precision Gold trading
          </p>
        </div>

        {/* Steps */}
        <div className="grid md:grid-cols-3 gap-12 relative">
          {/* Connection Lines (Desktop) */}
          <div className="hidden md:block absolute top-16 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-gray-700 to-transparent" />

          {steps.map((step, index) => (
            <div key={index} className="relative">
              {/* Step Card */}
              <div className="relative flex flex-col items-center text-center group">
                {/* Number Badge */}
                <div className={`absolute -top-6 text-7xl font-bold text-${step.color}/10 group-hover:text-${step.color}/20 transition-colors duration-300`}>
                  {step.number}
                </div>

                {/* Icon Circle */}
                <div className={`relative z-10 w-20 h-20 rounded-full bg-gradient-to-br from-${step.color} to-${step.color}/70 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg shadow-${step.color}/50`}>
                  <div className="text-white">
                    {step.icon}
                  </div>
                </div>

                {/* Content */}
                <h3 className="text-2xl font-bold mb-3 text-white">
                  {step.title}
                </h3>
                <p className="text-gray-400 leading-relaxed max-w-xs">
                  {step.description}
                </p>

                {/* Animated Arrow (Desktop) */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-16 -right-6 text-gray-700">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="animate-pulse">
                      <path d="M5 12h14m-7-7l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-16">
          <p className="text-gray-400 mb-6">
            Ready to transform your trading strategy?
          </p>
          <a
            href="/login"
            className="inline-flex items-center gap-2 px-8 py-4 bg-white text-gray-900 rounded-lg font-semibold hover:bg-gray-100 transition-all duration-300 hover:scale-105 shadow-lg"
          >
            Get Started Now
          </a>
        </div>
      </div>
    </section>
  );
}
