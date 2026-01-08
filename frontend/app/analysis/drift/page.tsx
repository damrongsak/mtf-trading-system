import React from 'react';
import { DriftDashboard } from '@/components/analysis/DriftDashboard';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'System Drift Analysis | MTF Olympus',
  description: 'Monitor strategy drift and filter rates.',
};

export default function DriftWaitPage() {
  return (
    <div className="container mx-auto py-8">
      <DriftDashboard />
    </div>
  );
}
