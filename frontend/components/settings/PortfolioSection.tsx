'use client';

import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences, getFunds, updateFund } from '@/lib/api';
import { type Fund, type StrategyType } from '@/lib/api/types';
import { BrokerAccountsSection } from './BrokerAccountsSection';
import { FundManagementModal } from './FundManagementModal';
import { Settings, Lock } from 'lucide-react';

export function PortfolioSection() {
  const [funds, setFunds] = useState<Fund[]>([]);
  const [selectedFundId, setSelectedFundId] = useState<string | null>(null);
  const [activeFund, setActiveFund] = useState<Fund | null>(null);
  
  // Supported Symbols State (Linked to UserPrefs still? No, Fund.asset_classes handles broader scope, but Symbols might be Account level. 
  // Wait, UserPrefs.supported_symbols is moved to BrokerAccount. 
  // PortfolioSection handles Fund settings. 
  // BrokerAccountsSection handles Broker settings.
  // Maybe we remove "Supported Symbols" from here entirely? Or move it to BrokerAccount section?
  // The task says "Update BrokerAccountsSection to manage supported_symbols".
  // So I should REMOVE supported symbols from here.
  
  // Basic Risk Parameters (Fund Level)
  const [strategyType, setStrategyType] = useState<StrategyType>('MTF_SMC_BASIC');
  const [maxRisk, setMaxRisk] = useState(10.0);
  const [defaultLotSize, setDefaultLotSize] = useState(0.01);
  const [maxDrawdown, setMaxDrawdown] = useState<number | null>(null);
  
  // Advanced Risk Parameters
  const [maxBeta, setMaxBeta] = useState(0.35);
  const [grossExposure, setGrossExposure] = useState(100.0);
  const [netExposure, setNetExposure] = useState(15.0);
  const [positionLimitSingle, setPositionLimitSingle] = useState(3.0);
  const [positionLimitSector, setPositionLimitSector] = useState(10.0);
  
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isManageModalOpen, setIsManageModalOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedFundId && funds.length > 0) {
        const fund = funds.find(f => f.id === selectedFundId);
        if (fund) {
            setActiveFund(fund);
            // Initialize form with Fund's values
            setStrategyType(fund.strategy_type);
            setMaxRisk(fund.max_risk_per_trade);
            setDefaultLotSize(fund.default_lot_size);
            setMaxDrawdown(fund.max_drawdown_threshold);
            setMaxBeta(fund.max_portfolio_beta || 0.35);
            setGrossExposure(fund.gross_exposure_limit || 100.0);
            setNetExposure(fund.net_exposure_limit || 15.0);
            setPositionLimitSingle(fund.position_limit_single || 3.0);
            setPositionLimitSector(fund.position_limit_sector || 10.0);
        }
    } else {
        setActiveFund(null);
    }
  }, [selectedFundId, funds]);

  const loadData = async () => {
    try {
      const [prefs, fundsData] = await Promise.all([getPreferences(), getFunds()]);
      setFunds(fundsData);
      setSelectedFundId(prefs.default_fund_id);
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
      // 1. Update Default Fund Preference
      await updatePreferences({
        default_fund_id: selectedFundId,
      });

      // 2. Update Fund Settings (if fund selected)
      if (selectedFundId && activeFund) {
          // Check permissions? API will enforce.
          await updateFund(selectedFundId, {
            strategy_type: strategyType,
            max_risk_per_trade: maxRisk,
            default_lot_size: defaultLotSize,
            max_drawdown_threshold: maxDrawdown,
            max_portfolio_beta: maxBeta,
            gross_exposure_limit: grossExposure,
            net_exposure_limit: netExposure,
            position_limit_single: positionLimitSingle,
            position_limit_sector: positionLimitSector
          });
          
          // Refresh funds data to sync
          const updatedFunds = await getFunds();
          setFunds(updatedFunds);
      }

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
  const canEdit = !!activeFund && (activeFund.role === 'OWNER' || activeFund.role === 'MANAGER');

  return (
    <div className="space-y-6">
      <FundManagementModal 
        isOpen={isManageModalOpen} 
        onClose={() => setIsManageModalOpen(false)} 
        onSuccess={loadData}
        funds={funds}
        currentFundId={selectedFundId}
      />
      
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

      {/* Default Fund Selector */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Active Fund</h2>
            <button 
                onClick={() => setIsManageModalOpen(true)}
                className="flex items-center gap-2 text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
            >
                <Settings size={14} />
                Manage Funds
            </button>
        </div>
        <select
          value={selectedFundId || ''}
          onChange={(e) => setSelectedFundId(e.target.value || null)}
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
        >
          <option value="">Select a fund to manage...</option>
          {funds
            .filter(fund => fund.role === 'OWNER')
            .sort((a, b) => (a.owner_name || '').localeCompare(b.owner_name || ''))
            .map((fund) => (
              <option key={fund.id} value={fund.id}>
                {fund.owner_name} - {fund.name}
              </option>
          ))}
        </select>
        {!selectedFundId && (
             <p className="text-yellow-500 text-sm mt-3 flex items-center gap-2">
                 <Lock size={14} />
                 Select a fund to edit risk parameters.
             </p>
        )}
      </div>

      {/* Risk Parameters Form - Only visible if fund selected */}
      <div className={`transition-opacity duration-200 ${canEdit ? 'opacity-100' : 'opacity-50 pointer-events-none grayscale'}`}>
          
        {/* Strategy Type Selector */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Strategy Profile</h2>
            <select
                value={strategyType}
                onChange={(e) => setStrategyType(e.target.value as StrategyType)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            >
                <option value="MTF_SMC_BASIC">MTF SMC Basic (Gold/Forex)</option>
                <option value="LONG_SHORT_EQUITY">Long/Short Equity</option>
                <option value="MACRO_TACTICAL">Macro Tactical</option>
                <option value="MULTI_ASSET">Multi-Asset</option>
            </select>
             <p className="text-xs text-gray-500 mt-2">
                Determines available asset classes and advanced risk settings visibility.
            </p>
        </div>

          {/* Basic Risk Parameters */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-6">
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
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-6">
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
      </div>

      {/* Broker Accounts */}
      <BrokerAccountsSection fundId={selectedFundId} />

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving || !canEdit}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Portfolio Settings'}
        </button>
      </div>
    </div>
  );
}
