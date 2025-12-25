'use client';

import React, { useMemo } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import Plot with no SSR to avoid "window is not defined"
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface InteractiveBacktestChartProps {
  plotJson: string;
}

export default function InteractiveBacktestChart({ plotJson }: InteractiveBacktestChartProps) {
  const { data, layout } = useMemo(() => {
    try {
      if (!plotJson) return { data: [], layout: {} };
      const parsed = JSON.parse(plotJson);
      return {
        data: parsed.data || [],
        layout: parsed.layout || {}
      };
    } catch (e) {
      console.error("Failed to parse Plotly JSON", e);
      return { data: [], layout: {} };
    }
  }, [plotJson]);

  // Dark mode adjustments for vectorbt default plots
  // Vectorbt usually produces dark plots, but we can override if needed.
  // We'll enforce transparent background to match our UI.
  const finalLayout = useMemo(() => {
    return {
      ...layout,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {
        color: '#94a3b8' // Slate-400
      },
      autosize: true, // Important for responsive width
      margin: { l: 40, r: 20, t: 30, b: 30 },
      showlegend: true,
      legend: {
          orientation: 'h',
          y: 1.1,
          font: { color: '#cbd5e1' }
      },
      // Darken grid lines for X and Y axes
      xaxis: {
        ...(layout.xaxis || {}),
        gridcolor: '#1e293b', // slate-800
        zerolinecolor: '#334155',
        tickcolor: '#334155'
      },
      yaxis: {
        ...(layout.yaxis || {}),
        gridcolor: '#1e293b', // slate-800
        zerolinecolor: '#334155',
        tickcolor: '#334155'
      },
      // Handle subplots if they exist (yaxis2, yaxis3, etc.)
      ...Object.keys(layout).reduce((acc, key) => {
        if (key.startsWith('xaxis') || key.startsWith('yaxis')) {
           acc[key] = {
             ...layout[key],
             gridcolor: '#1e293b',
             zerolinecolor: '#334155',
             tickcolor: '#334155'
           };
        }
        return acc;
      }, {} as any)
    };
  }, [layout]);

  if (!data || data.length === 0) {
      return <div className="text-center text-gray-500 py-10">No interactive plot data available</div>;
  }

  return (
    <div className="w-full h-full min-h-[850px] bg-slate-950">
      <Plot
        data={data}
        layout={finalLayout}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ responsive: true, displayModeBar: true }}
      />
    </div>
  );
}
