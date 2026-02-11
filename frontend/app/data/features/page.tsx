import { FeatureMatrix } from '@/components/data/FeatureMatrix';

export default function FeaturesPage() {
    return (
        <div className="container mx-auto py-8">
            <h1 className="text-3xl font-bold mb-6 text-white tracking-tight">Market Features</h1>
            
            <div className="mb-8">
                <FeatureMatrix />
            </div>
            
            <div className="grid gap-6 md:grid-cols-2">
                <div className="bg-gray-950 p-6 rounded-xl border border-gray-800">
                    <h3 className="text-lg font-bold text-white mb-3">About Feature Matrix</h3>
                    <p className="text-sm text-gray-400 leading-relaxed">
                        The Feature Matrix provides a real-time view of technical indicators and quantitative 
                        signals across all active market symbols. These features are calculated using 
                        institutional-grade algorithms in our Strategy Core and streamed directly to the dashboard.
                    </p>
                </div>
                
                <div className="bg-gray-950 p-6 rounded-xl border border-gray-800">
                    <h3 className="text-lg font-bold text-white mb-3">Direct Edge</h3>
                    <p className="text-sm text-gray-400 leading-relaxed">
                        Use these features to identify overbought/oversold regimes (RSI), institutional 
                        structure shifts (SMC), and volatility expansions (ATR/BB). These inputs power our 
                        AI Analyst&apos;s decision-making process.
                    </p>
                </div>
            </div>
        </div>
    );
}
