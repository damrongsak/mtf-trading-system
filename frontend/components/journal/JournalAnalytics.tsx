import React, { useEffect, useState } from 'react';
import { getJournalStats, getEquityCurve, getPatternAnalysis } from '@/lib/api/journal';
import { JournalStatsResponse, EquityCurvePoint, PatternAnalysisResponse } from '@/lib/api/types';
import StatsCards from './analytics/StatsCards';
import EquityChart from './analytics/EquityChart';
import PatternsGrid from './analytics/PatternsGrid';
import { Loader2 } from 'lucide-react';

const JournalAnalytics: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stats, setStats] = useState<JournalStatsResponse | null>(null);
    const [equityCurve, setEquityCurve] = useState<EquityCurvePoint[]>([]);
    const [patterns, setPatterns] = useState<PatternAnalysisResponse | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const [statsData, equityData, patternsData] = await Promise.all([
                    getJournalStats(),
                    getEquityCurve(),
                    patternsData = getPatternAnalysis()
                ]);

                setStats(statsData);
                setEquityCurve(equityData);
                setPatterns(patternsData);
            } catch (err) {
                console.error("Failed to fetch analytics:", err);
                setError("Failed to load analytics data. Please try again.");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-96">
                <Loader2 className="animate-spin text-emerald-500" size={48} />
                <span className="ml-3 text-gray-400">Analyzing Trading Performance...</span>
            </div>
        );
    }

    if (error || !stats || !patterns) {
        return (
            <div className="flex justify-center items-center h-96 text-red-400">
                {error || "No data available."}
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header / Context */}
            <div>
                <h2 className="text-2xl font-bold text-white mb-2">Performance Analytics</h2>
                <p className="text-gray-400">Deep dive into your trading psychology and results.</p>
            </div>

            {/* 1. Key Metrics Cards */}
            <StatsCards stats={stats} />

            {/* 2. Equity Curve */}
            <EquityChart data={equityCurve} />

            {/* 3. Pattern Recognition Heatmap */}
            <PatternsGrid patterns={patterns} />
        </div>
    );
};

export default JournalAnalytics;
