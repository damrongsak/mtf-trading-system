'use client';

import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences, type StrategyType, type AssetClass } from '@/lib/api';

const STRATEGY_INFO: Record<StrategyType, { description: string; features: string[] }> = {
  MTF_SMC_BASIC: {
    description: 'Multi-Timeframe Smart Money Concepts for XAU/USD trading',
    features: ['4H/1H/15m analysis', 'Order blocks', 'Fibonacci retracements', 'XAU/USD only'],
  },
  LONG_SHORT_EQUITY: {
    description: 'Equity Long/Short with dispersion harvesting',
    features: ['Sector rotation', 'Factor-aware selection', 'Gross exposure 180-220%', 'Multiple asset classes'],
  },
  MACRO_TACTICAL: {
    description: 'Global macro positioning based on policy divergence',
    features: ['Currency pairs', 'Interest rate plays', 'Tactical duration', 'Cross-country analysis'],
  },
  MULTI_ASSET: {
    description: 'Full portfolio construction across asset classes',
    features: ['Equity + FX + Commodities + Fixed Income', 'Advanced risk management', 'Portfolio-level optimization'],
  },
};

export function StrategySection() {
  const [strategyType, setStrategyType] = useState<StrategyType>('MTF_SMC_BASIC');
  const [assetClasses, setAssetClasses] = useState<AssetClass[]>(['FX']);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      const prefs = await getPreferences();
      setStrategyType(prefs.strategy_type);
      setAssetClasses(prefs.asset_classes as AssetClass[]);
    } catch {
      setMessage({ type: 'error', text: 'Failed to load preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      await updatePreferences({
        strategy_type: strategyType,
        asset_classes: assetClasses,
      });
      setMessage({ type: 'success', text: 'Strategy configuration saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: (error as Error).message || 'Failed to save configuration' });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleAssetClass = (assetClass: AssetClass) => {
    if (assetClasses.includes(assetClass)) {
      setAssetClasses(assetClasses.filter((ac) => ac !== assetClass));
    } else {
      setAssetClasses([...assetClasses, assetClass]);
    }
  };

  if (isLoading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  const isAdvancedStrategy = strategyType !== 'MTF_SMC_BASIC';

  return (
    <div className="space-y-6">
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-900/20 border border-green-700 text-green-400'
              : 'bg-red-900/20 border border-red-700 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Strategy Type Selection */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Strategy Type</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(Object.keys(STRATEGY_INFO) as StrategyType[]).map((type) => (
            <button
              key={type}
              onClick={() => setStrategyType(type)}
              className={`p-4 rounded-lg border-2 text-left transition-all ${
                strategyType === type
                  ? 'border-blue-500 bg-blue-900/20'
                  : 'border-gray-700 bg-gray-800 hover:border-gray-600'
              }`}
            >
              <h3 className="font-semibold text-white mb-2">
                {type.replace(/_/g, ' ')}
              </h3>
              <p className="text-sm text-gray-400 mb-3">
                {STRATEGY_INFO[type].description}
              </p>
              <ul className="text-xs text-gray-500 space-y-1">
                {STRATEGY_INFO[type].features.map((feature, idx) => (
                  <li key={idx}>• {feature}</li>
                ))}
              </ul>
            </button>
          ))}
        </div>
      </div>

      {/* Asset Classes (for advanced strategies) */}
      {isAdvancedStrategy && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Asset Classes</h2>
          <p className="text-sm text-gray-400 mb-4">
            Select the asset classes you want to trade in this strategy
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {(['EQUITY', 'FX', 'COMMODITIES', 'FIXED_INCOME'] as AssetClass[]).map((assetClass) => (
              <button
                key={assetClass}
                onClick={() => toggleAssetClass(assetClass)}
                className={`p-4 rounded-lg border-2 transition-all ${
                  assetClasses.includes(assetClass)
                    ? 'border-green-500 bg-green-900/20'
                    : 'border-gray-700 bg-gray-800 hover:border-gray-600'
                }`}
              >
                <span className="text-white font-medium">{assetClass}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Strategy Configuration'}
        </button>
      </div>
    </div>
  );
}
