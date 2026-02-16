import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { BacktestMetrics } from '@/lib/api/generated';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SystemRadarChartProps {
  metrics: BacktestMetrics;
  className?: string;
}

export const SystemRadarChart: React.FC<SystemRadarChartProps> = ({ metrics, className }) => {
  // Normalize metrics to 0-10 scale for the chart
  // We need to define "good" threshold values for scaling.
  
  const normalize = (value: number, min: number, max: number) => {
      if (value === undefined || value === null) return 0;
      const clamped = Math.min(Math.max(value, min), max);
      // Linear mapping to 0-10
      return ((clamped - min) / (max - min)) * 10;
  };
  
  // Metric Definitions & Scaling Logic
  // 1. Reward (Sharpe Ratio) -> Target > 1.0, Max 3.0
  const rewardScore = normalize(metrics.sharpe_ratio ?? 0, 0, 3.0);
  
  // 2. Consistency (K-Ratio) -> Target > 0.5, Max 2.0 (Note: K-Ratio can be high for very consistent)
  const consistencyScore = normalize((metrics as any).k_ratio ?? 0, 0, 2.0);
  
  // 3. Efficiency (Profit Factor) -> Target > 1.5, Max 3.0
  const efficiencyScore = normalize((metrics as any).profit_factor ?? 1.0, 1.0, 4.0);
  
  // 4. Safety (Max Drawdown Inverse) -> Target < 20%, MaxScore at 0%
  // 10 - (DD% / 5) -> 50% DD = 0 score. 0% DD = 10 score.
  // Using max_drawdown_percent (e.g., 10.5 for 10.5%)
  const safetyScore = Math.max(0, 10 - ((metrics.max_drawdown_percent ?? 0)) / 4); // 40% DD = 0
  
  // 5. Reliability (Win Rate) -> Target 50%+, Max 80% (Too high might be overfitting)
  // Scale 30% to 80% -> 0 to 10
  const reliabilityScore = normalize(metrics.win_rate ?? 0, 30, 80);
  
  // 6. Payoff (Reward to Risk) -> Target 1:1 to 3:1
  const payoffScore = normalize((metrics as any).reward_to_risk_ratio ?? 0, 0.5, 4.0);

  // 7. Tail Risk (Kurtosis) -> Lower is better (Normal dist = 3, Excess = 0)
  // High Kurtosis = Fat Tails (Risk of blowup). 
  // We want LOW Excess Kurtosis (close to 0 or negative).
  // Scale: 10 (Good) to 0 (Bad). 
  // Let's say Excess Kurtosis > 10 is bad (0 score). < 1 is good (10 score).
  const kurtosisVal = (metrics as any).kurtosis ?? 0;
  const tailRiskScore = Math.max(0, 10 - Math.max(0, kurtosisVal - 1)); 

  const data = [
    { subject: 'Reward', A: rewardScore, fullMark: 10, val: metrics.sharpe_ratio?.toFixed(2) },
    { subject: 'Consistency', A: consistencyScore, fullMark: 10, val: (metrics as any).k_ratio?.toFixed(2) },
    { subject: 'Efficiency', A: efficiencyScore, fullMark: 10, val: (metrics as any).profit_factor?.toFixed(2) },
    { subject: 'Safety', A: safetyScore, fullMark: 10, val: `${metrics.max_drawdown_percent?.toFixed(1)}%` },
    { subject: 'Reliability', A: reliabilityScore, fullMark: 10, val: `${metrics.win_rate?.toFixed(1)}%` },
    { subject: 'Payoff', A: payoffScore, fullMark: 10, val: (metrics as any).reward_to_risk_ratio?.toFixed(2) },
    { subject: 'Tail Risk', A: tailRiskScore, fullMark: 10, val: (metrics as any).kurtosis?.toFixed(2) },
  ];
  
  // Calculate System Quality Score (Average Area)
  const systemScore = (rewardScore + consistencyScore + efficiencyScore + safetyScore + reliabilityScore + payoffScore) / 6;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="flex justify-between items-center text-sm font-medium">
            System Evaluation
            <span className={`text-xs px-2 py-1 rounded-full ${
                systemScore >= 7 ? 'bg-green-500/20 text-green-400' : 
                systemScore >= 5 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
            }`}>
                Score: {systemScore.toFixed(1)}/10
            </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 10]} tick={false} axisLine={false} />
              <Radar
                name="System"
                dataKey="A"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="#8b5cf6"
                fillOpacity={0.4}
              />
              <Tooltip 
                content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                        <div className="bg-slate-900 border border-slate-700 p-2 rounded shadow-lg text-xs">
                        <p className="font-bold text-slate-200">{d.subject}</p>
                        <p className="text-slate-400">Score: {d.A.toFixed(1)}/10</p>
                        <p className="text-violet-400">Value: {d.val}</p>
                        </div>
                    );
                    }
                    return null;
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
