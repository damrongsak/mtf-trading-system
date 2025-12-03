'use client';

import Link from 'next/link';
import { TrendingUp } from 'lucide-react';

export function GuestHeader() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-lg">
      <nav className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 text-white hover:text-accent-blue transition-colors">
          <TrendingUp className="w-6 h-6" />
          <span className="text-xl font-bold">MTF Trading</span>
        </Link>

        {/* Navigation Links */}
        <div className="hidden md:flex items-center gap-8 text-sm">
          <Link href="#features" className="text-gray-400 hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#signals-preview" className="text-gray-400 hover:text-white transition-colors">
            Signals
          </Link>
          <Link href="#how-it-works" className="text-gray-400 hover:text-white transition-colors">
            How It Works
          </Link>
        </div>

        {/* Auth Buttons */}
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="px-6 py-2 bg-gradient-to-r from-accent-blue to-purple-600 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-accent-blue/50 transition-all duration-300 text-sm"
          >
            Get Started
          </Link>
        </div>
      </nav>
    </header>
  );
}
