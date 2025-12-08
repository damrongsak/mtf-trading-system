'use client';

import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences, getFunds, type Fund } from '@/lib/api';

export function PortfolioSection() {
  const [funds, setFunds] = useState<Fund[]>([]);
  const [selectedFundId, setSelectedFundId] = useState<string | null>(null);
  const [strategyType, setStrategyType] = useState<string>('MTF_SMC_BASIC');
  
  // Basic Risk Parameters
  const [maxRisk, setMaxRisk] = useState(10.0);
  const [defaultLotSize, setDefaultLotSize] = useState(0.01);
  const [maxDrawdown, setMaxDrawdown] = useState<number | null>(null);
  
  // Advanced Risk Parameters (L/S & Multi-Asset)
  const [maxBeta, setMaxBeta] = useState(0.35);
  const [grossExposure, setGrossExposure] = useState(100.0);
  const [netExposure, setNetExposure] = useState(15.0);
  const [positionLimitSingle, setPositionLimitSingle] = useState(3.0);
  const [positionLimitSector, setPositionLimitSector] = useState(10.0);
  
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [prefs, fundsData] = await Promise.all([getPreferences(), getFunds()]);
      
      setFunds(fundsData);
      setSelectedFundId(prefs.default_fund_id);
      setStrategyType(prefs.strategy_type);
      setMaxRisk(prefs.max_risk_per_trade);
      setDefaultLotSize(prefs.default_lot_size);
      setMaxDrawdown(prefs.max_drawdown_threshold);
      setMaxBeta(prefs.max_portfolio_beta || 0.35);
      setGrossExposure(prefs.gross_exposure_limit || 100.0);
      setNetExposure(prefs.net_exposure_limit || 15.0);
      setPositionLimitSingle(prefs.position_limit_single || 3.0);
      setPositionLimitSector(prefs.position_limit_sector || 10.0);
    } catch {
      setMessage({ type: 'error', text: 'Failed to load portfolio settings' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      await updatePreferences({
        default_fund_id: selectedFundId,
        max_risk_per_trade: maxRisk,
        default_lot_size: defaultLotSize,
        max_drawdown_threshold: maxDrawdown,
        max_portfolio_beta: maxBeta,
        gross_exposure_limit: grossExposure,
        net_exposure_limit: netExposure,
        position_limit_single: positionLimitSingle,
        position_limit_sector: positionLimitSector,
      });
      setMessage({ type: 'success', text: 'Portfolio settings saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: (error as Error).message || 'Failed to save settings' });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  const isAdvanced = strategyType !== 'MTF_SMC_BASIC';

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

      {/* Default Fund */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Default Fund</h2>
        <select
          value={selectedFundId || ''}
          onChange={(e) => setSelectedFundId(e.target.value || null)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
        >
          <option value="">No default fund</option>
          {funds.map((fund) => (
            <option key={fund.id} value={fund.id}>
              {fund.name} {fund.role && `(${fund.role})`}
            </option>
          ))}
        </select>
      </div>

      {/* Basic Risk Parameters */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Risk Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Max Risk per Trade (USD)</label>
            <input
              type="number"
              step="0.01"
              value={maxRisk}
              onChange={(e) => setMaxRisk(parseFloat(e.target.value))}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">Default: $10.00</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Default Lot Size</label>
            <input
              type="number"
              step="0.01"
              value={defaultLotSize}
              onChange={(e) => setDefaultLotSize(parseFloat(e.target.value))}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">Minimum: 0.01</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Max Drawdown Threshold (%)</label>
            <input
              type="number"
              step="0.1"
              value={maxDrawdown || ''}
              onChange={(e) => setMaxDrawdown(e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="Optional"
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Advanced Risk Parameters */}
      {isAdvanced && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-2">Advanced Risk Parameters</h2>
          <p className="text-sm text-gray-400 mb-4">For Long/Short & Multi-Asset strategies</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Max Portfolio Beta</label>
              <input
                type="number"
                step="0.01"
                value={maxBeta}
                onChange={(e) => setMaxBeta(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">Default: 0.35</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Gross Exposure Limit (%)</label>
              <input
                type="number"
                step="1"
                value={grossExposure}
                onChange={(e) => setGrossExposure(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">L/S: 180-220%</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Net Exposure Limit (%)</label>
              <input
                type="number"
                step="1"
                value={netExposure}
                onChange={(e) => setNetExposure(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">0-15% net long</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Position Limit - Single (%)</label>
              <input
                type="number"
                step="0.1"
                value={positionLimitSingle}
                onChange={(e) => setPositionLimitSingle(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">Max 3% per name</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Position Limit - Sector (%)</label>
              <input
                type="number"
                step="0.1"
                value={positionLimitSector}
                onChange={(e) => setPositionLimitSector(parseFloat(e.target.value))}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">Max 10% per sector</p>
            </div>
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
          {isSaving ? 'Saving...' : 'Save Portfolio Settings'}
        </button>
      </div>
    </div>
  );
}
