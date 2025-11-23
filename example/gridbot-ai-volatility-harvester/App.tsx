
import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { StatsHeader } from './components/StatsHeader';
import { MainChart } from './components/MainChart';
import { TradeLog } from './components/TradeLog';
import { GeminiAdvisor } from './components/GeminiAdvisor';
import { MonteCarloModal } from './components/MonteCarloModal';
import { useGridBot } from './hooks/useGridBot';
import { runMonteCarlo } from './services/simulationEngine';
import { MonteCarloStats, BotConfig } from './types';

const App: React.FC = () => {
  const { 
    config, 
    setConfig, 
    isRunning, 
    setIsRunning, 
    currentPrice, 
    stats, 
    trades,
    activePositions,
    gridLevels,
    priceHistory,
    reset
  } = useGridBot();

  // Monte Carlo State
  const [isSimModalOpen, setIsSimModalOpen] = useState(false);
  const [simStats, setSimStats] = useState<MonteCarloStats | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);

  // Initialize grid on mount
  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRunSimulation = async () => {
    setIsSimModalOpen(true);
    setIsSimLoading(true);
    setSimStats(null);
    
    // Use timeout to allow UI to render modal first
    setTimeout(() => {
        const results = runMonteCarlo(config, 100, 1500); // 100 runs, 1500 ticks each
        setSimStats(results);
        setIsSimLoading(false);
    }, 100);
  };

  const handleApplyScenario = (overrides: Partial<BotConfig>) => {
      setConfig({
          ...config,
          ...overrides
      });
      // Optional: Reset immediately to show effect, or let user click reset
      // reset(); 
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-200 font-sans selection:bg-blue-500/30">
      {/* Left Sidebar */}
      <Sidebar 
        config={config} 
        setConfig={setConfig} 
        isRunning={isRunning} 
        setIsRunning={setIsRunning}
        onReset={reset}
        currentPrice={currentPrice}
        onRunSimulation={handleRunSimulation}
      />

      {/* Main Content */}
      <main className="pl-[340px] p-6 h-screen overflow-y-auto">
        <div className="max-w-[1600px] mx-auto">
          
          {/* Header Stats */}
          <StatsHeader 
            stats={stats} 
            currentPrice={currentPrice} 
            equityHistory={[]} 
            assetSymbol={config.assetSymbol}
          />

          {/* Chart Area */}
          <div className="mb-4">
             <MainChart 
               data={priceHistory} 
               gridLevels={gridLevels} 
               currentPrice={currentPrice}
               config={config}
               trades={trades}
             />
          </div>

          {/* Bottom Panels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <TradeLog 
              trades={trades} 
              activePositions={activePositions} 
              gridLevels={gridLevels} 
            />
            <GeminiAdvisor 
              stats={stats} 
              config={config} 
              onApplyScenario={handleApplyScenario}
            />
          </div>

        </div>
      </main>

      {/* Analytics Modal */}
      <MonteCarloModal 
        isOpen={isSimModalOpen}
        onClose={() => setIsSimModalOpen(false)}
        stats={simStats}
        config={config}
        isLoading={isSimLoading}
      />
    </div>
  );
};

export default App;
