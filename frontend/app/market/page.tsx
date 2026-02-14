'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { IndicatorData } from '@/components/charts/CandleChart';
import { Time } from 'lightweight-charts';
import { fetchCandles, Candle } from '@/lib/api/market';

import { fetchSystemConfig } from '@/lib/api/system';
import { 
    calculateEMA, calculateRSI, calculateATR, calculateMACD, calculateADX, calculateSMC, 
    SMCResponse, SMCStructureLabel, SMCOrderBlock 
} from '@/lib/api/analysis';
import { useLivePrices } from '@/lib/hooks/useLivePrices';
import { logger } from '@/lib/api/app-logger';
import { ChartPriceLine } from '@/components/charts/CandleChart';
import { SeriesMarker } from 'lightweight-charts';

import { cn } from '@/lib/utils';
import { RefreshCcw, Activity, TrendingUp, LayoutTemplate } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { OpenInterestAnalytics } from '@/components/data/OpenInterestAnalytics';
import { useBrokerReference } from '@/context/BrokerReferenceContext';
import { useAccount } from '@/context/AccountContext';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle, PanelImperativeHandle } from "react-resizable-panels";
import { OrderPanel } from '@/components/market/OrderPanel';
import { AccountPanel } from '@/components/market/AccountPanel';
import { usePersistentState } from '@/lib/hooks/usePersistentState';
import { useGammaLevels } from '@/lib/hooks/useGammaLevels';

// Dynamic Imports for Heavy Charts
const CandleChart = dynamic(() => import('@/components/charts/CandleChart').then(mod => mod.CandleChart), { ssr: false });
const ChartContainer = dynamic(() => import('@/components/charts/ChartContainer').then(mod => mod.ChartContainer), { ssr: false });
const IndicatorChart = dynamic(() => import('@/components/charts/IndicatorChart').then(mod => mod.IndicatorChart), { ssr: false });

// --- Types ---

const DEFAULT_TIMEFRAMES = ['M5', 'M15', 'H1', 'H4', 'D', 'W', 'M'];

export default function MarketPage() {
  // --- State: Market Data ---
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = usePersistentState<string>('mtf_symbol', 'XAUUSD');
  const [timeframe, setTimeframe] = usePersistentState<string>('mtf_timeframe', 'H1');
  const [availableTimeframes, setAvailableTimeframes] = useState<string[]>(DEFAULT_TIMEFRAMES);
  const [loading, setLoading] = useState(false);


  // --- State: Indicators ---
  const [showEMA, setShowEMA] = usePersistentState<boolean>('mtf_show_ema', false);
  const [showEMA50] = usePersistentState<boolean>('mtf_show_ema50', true);
  const [showRSI, setShowRSI] = usePersistentState<boolean>('mtf_show_rsi', false);
  const [showATR, setShowATR] = usePersistentState<boolean>('mtf_show_atr', true);
  const [showMACD, setShowMACD] = usePersistentState<boolean>('mtf_show_macd', true);
  const [showADX, setShowADX] = usePersistentState<boolean>('mtf_show_adx', false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);
  const [showSMC, setShowSMC] = usePersistentState<boolean>('mtf_show_smc', false);
  const [showGamma, setShowGamma] = usePersistentState<boolean>('mtf_show_gamma', false);
  const [smcMarkers, setSmcMarkers] = useState<SeriesMarker<Time>[]>([]);
  const [smcPriceLines, setSmcPriceLines] = useState<ChartPriceLine[]>([]);
  const [orderLines, setOrderLines] = useState<ChartPriceLine[]>([]);
  
  // Ref bypass for components with problematic ref types
  const AnyPanel = Panel as any;

  // --- Lifted Order State ---
  const [slPrice, setSlPrice] = useState<number>(0);
  const [tpPrice, setTpPrice] = useState<number>(0);
  const [limitPrice, setLimitPrice] = useState<number>(0);
  const [slMode, setSlMode] = usePersistentState<'PIPS' | 'PRICE'>('mtf_sl_mode', 'PIPS');
  const [tpMode, setTpMode] = usePersistentState<'PIPS' | 'PRICE'>('mtf_tp_mode', 'PIPS');

  // --- State: UI Layout ---
  const [showAnalytics, setShowAnalytics] = useState(false); // Default hidden for cleaner look
  const [showAccountPanel] = usePersistentState<boolean>('mtf_show_account_panel', true);
  const [mounted, setMounted] = useState(false);
  
  const accountPanelRef = useRef<PanelImperativeHandle>(null);
  const orderPanelRef = useRef<PanelImperativeHandle>(null);


  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Prevent flash of unstyled content (FOUC) / layout jump by waiting for mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const { selectedAccount } = useAccount();

  // Determine Data Source
  const dataSource = React.useMemo(() => {
      // Default to CTRADER unless explicitly OANDA
      if (selectedAccount?.broker_name === 'OANDA') return 'OANDA';
      return 'CTRADER';
  }, [selectedAccount]);

  const { prices, connected } = useLivePrices([symbol], dataSource);
  const { formatPrice, getInstrument } = useBrokerReference();
  const brokerSymbols = useBrokerReference().symbols;

  // --- Handlers ---
  const handleLineDrag = (title: string, price: number) => {
      const instrument = getInstrument(symbol);
      // Standardized 'digits' takes precedence
      const precision = (instrument?.details?.digits ?? instrument?.details?.displayPrecision ?? 5) as number;
      const rounded = parseFloat(price.toFixed(precision));
      
      if (title === 'SL') {
          setSlPrice(rounded);
          setSlMode('PRICE'); // Dragging implies Fixed Price intent
      }
      if (title === 'TP') {
          setTpPrice(rounded);
          setTpMode('PRICE'); // Dragging implies Fixed Price intent
      }
      if (title === 'ENTRY') setLimitPrice(rounded);
  };

  // --- Effects: Initialization ---
  useEffect(() => {
    fetchSystemConfig().then(config => {
        if (config.supported_timeframes && config.supported_timeframes.length > 0) {
            setAvailableTimeframes(config.supported_timeframes);
        }
    }).catch(err => logger.error("Failed to load system config", err));

    setMounted(true);
  }, []);

  // --- Effect: Validate Symbol on Broker Switch ---
  useEffect(() => {
      if (brokerSymbols.size > 0 && !brokerSymbols.has(symbol)) {
          // Identify if we can find a close match (e.g. XAU_USD -> XAUUSD)
          const clean = symbol.replace('_', '').replace('/', '');
          let match = '';
          
          for (const s of Array.from(brokerSymbols.keys())) {
               if (s.replace('_', '').replace('/', '') === clean) {
                   match = s;
                   break;
               }
          }

          if (match) {
              setSymbol(match);
          } else {
              // Fallback to first available
              const first = brokerSymbols.values().next().value;
              if (first) setSymbol(first.symbol);
          }
      }
  }, [brokerSymbols, symbol, setSymbol]);


  // --- Effects: Data Loading ---
  const loadData = useCallback(async () => {
    setLoading(true);
    setCandles([]); // Clear old data
    
    try {
      const data = await fetchCandles({ 
          symbol, 
          timeframe, 
          count: 500,
          data_source: dataSource
      });
      setCandles(data);
    } catch (error) {
      logger.error("Failed to fetch candles", error);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, dataSource]);

  useEffect(() => { loadData(); }, [loadData]);

  // --- Helpers ---
  const getTimeframeSeconds = (tf: string): number => {
    switch(tf) {
        case 'M1': return 60;
        case 'M5': return 300;
        case 'M15': return 900;
        case 'M30': return 1800;
        case 'H1': return 3600;
        case 'H4': return 14400;
        case 'D': return 86400;
        case 'W': return 604800;
        case 'M': return 2592000;
        default: return 3600;
    }
  };

  // --- Effects: Live Price Updates ---
  useEffect(() => {
      if (!prices[symbol] || prices[symbol].type !== 'PRICE') return;
      
      const latest = prices[symbol];
      const price = latest.bid; 

      // Update Title
      document.title = `${formatPrice(symbol, price)} | ${symbol.replace('_', '/')}`;

      setCandles(prev => {
          if (prev.length === 0) return prev;
          
          const last = { ...prev[prev.length - 1] };
          const tfSeconds = getTimeframeSeconds(timeframe);
          
          // Current time in seconds
          const now = Math.floor(Date.now() / 1000);
          
          // Last candle time in seconds (assuming timestamp is ISO string)
          const lastTime = new Date(last.timestamp).getTime() / 1000;
          
          const nextBoundary = Math.floor(now / tfSeconds) * tfSeconds;
          
          if (lastTime < nextBoundary) {
              // Create New Candle
              const newCandle: Candle = {
                  timestamp: new Date(nextBoundary * 1000).toISOString(),
                  open: price,
                  high: price,
                  low: price,
                  close: price,
                  volume: 0
              };
              return [...prev, newCandle];
          } else {
              // Update Existing Candle
              last.close = price;
              last.high = Math.max(last.high, price);
              last.low = Math.min(last.low, price);
              
              const newCandles = [...prev];
              newCandles[newCandles.length - 1] = last;
              return newCandles;
          }
      });
  }, [prices, symbol, timeframe, formatPrice]);

  // --- Effects: Indicators ---
  useEffect(() => {
    if (candles.length === 0) return;
    updateIndicators();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles.length, showEMA, showRSI, showATR, showMACD, showADX, symbol, timeframe]); 

  const updateIndicators = async () => {

      const closes = candles.map(c => c.close);
      if (closes.length === 0) return;

      const newInds: IndicatorData[] = [];
      const promises: Promise<void>[] = [];

      const tryCalc = async <T,>(fn: () => Promise<T>, pushFn: (res: T) => void) => {
          try {
              const res = await fn();
              pushFn(res);
          } catch(e) { logger.error("Indicator Calc Failed", e); }
      };

      // Queue all enabled indicators for parallel execution
      if (showEMA) {
          promises.push(tryCalc(
              () => calculateEMA({ data: closes, span: 200 }), 
              (res: number[]) => newInds.push({ name: 'EMA 200', data: res, color: '#3b82f6' })
          ));
      }
      if (showRSI) {
          promises.push(tryCalc(
              () => calculateRSI({ close: closes, window: 14 }), 
              (res: number[]) => newInds.push({ name: 'RSI 14', data: res, color: '#a855f7', priceScaleId: 'left' })
          ));
      }
      if (showATR) {
          promises.push(tryCalc(
              () => calculateATR({ high: candles.map(c => c.high), low: candles.map(c => c.low), close: closes, window: 14 }), 
              (res: number[]) => newInds.push({ name: 'ATR 14', data: res, color: '#ec4899', priceScaleId: 'left' })
          ));
      }
      if (showMACD) {
           promises.push(tryCalc(
               () => calculateMACD({ close: closes }), 
               (res) => {
                   // Zip MACD components; generated type properties might be undefined
                   if (!res.macd || !res.signal || !res.hist) return;

                   const macdData = res.macd.map((v: number | null | undefined, i: number) => ({
                       value: v ?? 0,
                       signal: res.signal?.[i] ?? 0,
                       hist: res.hist?.[i] ?? 0
                   }));
                   newInds.push({ name: 'MACD', data: macdData, color: '#06b6d4', priceScaleId: 'left' });
               }
           ));
      }
      if (showADX) {
          promises.push(tryCalc(
              () => calculateADX({ high: candles.map(c => c.high), low: candles.map(c => c.low), close: closes, length: 14 }), 
              (res) => {
                  if (!res.adx) return;
                  
                  // Zip ADX components
                  const adxData = res.adx.map((v: number | null, i: number) => ({
                      value: v ?? 0,
                      dmp: res.dmp?.[i] ?? 0,
                      dmn: res.dmn?.[i] ?? 0
                  }));
                  newInds.push({ name: 'ADX', data: adxData, color: '#eab308', priceScaleId: 'left' });
              }
           ));
      }
      
      await Promise.all(promises);
      setChartIndicators(newInds);
  };

  // --- Effect: SMC ---
  useEffect(() => {
    if (!showSMC || candles.length === 0) {
        setSmcMarkers([]);
        setSmcPriceLines([]);
        return;
    }

    const loadSMC = async () => {
         try {
             // 1. Fetch
             const res = await calculateSMC({
                 open: candles.map(c => c.open),
                 high: candles.map(c => c.high),
                 low: candles.map(c => c.low),
                 close: candles.map(c => c.close),
                 volume: candles.map(c => c.volume || 0),
             });
             
             // 2. Transform for Chart
             const newMarkers: SeriesMarker<Time>[] = [];
             const newPriceLines: ChartPriceLine[] = [];
             
             // Structure Labels
             if (res.structure && res.structure.labels) {
                 res.structure.labels.forEach((l: SMCStructureLabel) => {
                     // Generated type puts optional on everything, so safe check
                     if (l.index === undefined || l.text === undefined) return;

                     const candle = candles[l.index];
                     if (candle) {
                         newMarkers.push({
                             time: new Date(candle.timestamp).getTime() / 1000 as Time,
                             position: l.text.endsWith('H') ? 'aboveBar' : 'belowBar',
                             shape: 'arrowDown', // Placeholder, LWC only supports limited shapes
                             text: l.text,
                             color: l.text.endsWith('H') ? '#ef4444' : '#22c55e',
                          });
                     }
                 });
             }

             // Order Blocks
             if (res.order_blocks) {
                 res.order_blocks.forEach((ob: SMCOrderBlock) => {
                     if (ob.top === undefined || ob.bottom === undefined || ob.type === undefined) return;

                     newPriceLines.push({
                         price: ob.top,
                         color: ob.type === 'bullish' ? '#22c55e' : '#ef4444',
                         title: ob.type === 'bullish' ? 'Bull OB' : 'Bear OB',
                         lineStyle: 0,
                         lineWidth: 2,
                         axisLabelVisible: true
                     });
                     newPriceLines.push({
                         price: ob.bottom,
                         color: ob.type === 'bullish' ? '#22c55e' : '#ef4444',
                         lineStyle: 0,
                         lineWidth: 1,
                         axisLabelVisible: false
                     });
                 });
             }

            // Auto Fibs
            if (res.auto_fibs) {
                 Object.entries(res.auto_fibs).forEach(([level, price]) => {
                     const p = price as number;
                     if (p > 0) {
                         newPriceLines.push({
                             price: p,
                             color: '#fbbf24', // Amber-400
                             title: `Fib ${level}`,
                             lineStyle: 2, // Dashed
                             lineWidth: 1,
                             axisLabelVisible: true
                         });
                     }
                 });
            }

             setSmcMarkers(newMarkers);
             setSmcPriceLines(newPriceLines);

         } catch (e) {
             logger.error("SMC Calc Failed", e);
         }
    };
    
    loadSMC();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showSMC, candles.length, symbol, timeframe]); // Re-calc on data update (new candle only) or toggle
  
  // --- Derived Data ---
  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const prevClose = candles.length > 1 ? candles[candles.length - 2].close : currentPrice;
  const change = currentPrice - prevClose;
  const changePercent = prevClose ? (change / prevClose) * 100 : 0;
  const isUp = change >= 0;

  // --- Gamma Levels ---
  const { gammaPriceLines } = useGammaLevels(symbol, currentPrice, showGamma);


  // Trigger refresh function
  const handleOrderSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  // --- Render ---
  return (
    <div className="h-screen bg-black text-gray-300 font-sans selection:bg-blue-500/30 flex flex-col overflow-hidden">
        
        {/* Top Bar: Market Ticker */}
        <header className="border-b border-white/5 bg-gray-950/50 backdrop-blur-md z-40 h-14 flex items-center px-4 justify-between shrink-0">
            <div className="flex items-center gap-6">
                 {/* Symbol Selector embedded in header for quick switch */}
                <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-500/10 rounded-md">
                        <Activity size={18} className="text-blue-500" />
                    </div>
                     <Select value={symbol} onValueChange={setSymbol}>
                        <SelectTrigger className="w-[140px] h-8 bg-transparent border-none text-white font-bold text-lg focus:ring-0 px-0">
                             <SelectValue>{symbol.replace('_', '/')}</SelectValue>
                        </SelectTrigger>
                        <SelectContent className="bg-gray-900 border-gray-800">
                            {brokerSymbols.size > 0 ? (
                                Array.from(brokerSymbols.values()).map(s => (
                                    <SelectItem key={s.id} value={s.symbol} className="text-gray-300 focus:bg-gray-800 focus:text-white">
                                        {s.symbol.replace('_', '/')}
                                    </SelectItem>
                                ))
                            ) : (
                                <SelectItem value={symbol} disabled>{symbol.replace('_', '/')}</SelectItem>
                            )}
                        </SelectContent>
                    </Select>
                </div>

                <div className="h-6 w-px bg-white/10" />

                {/* Price Stats */}
                <div className="flex items-baseline gap-3">
                    <span className="text-xl font-mono font-medium text-white tracking-tight">
                        {formatPrice(symbol, currentPrice)}
                    </span>
                    <span className={cn("text-sm font-mono font-medium flex items-center", isUp ? "text-emerald-400" : "text-rose-400")}>
                        {isUp ? <TrendingUp size={14} className="mr-1" /> : <TrendingUp size={14} className="mr-1 rotate-180" />}
                        {formatPrice(symbol, change)} ({changePercent.toFixed(2)}%)
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-gray-500">
                <button 
                    onClick={() => {
                        const panel = accountPanelRef.current;
                        if (panel) {
                            const size = panel.getSize();
                            const currentSize = typeof size === 'number' ? size : (size as any).asPercentage;
                            panel.resize(currentSize < 10 ? 30 : 4);
                        }
                    }} 
                    className={cn("p-1.5 rounded hover:bg-white/10 transition-colors", "text-blue-400 bg-blue-500/10")}
                    title="Toggle Account Panel"
                >
                    <LayoutTemplate size={18} />
                </button>
                <div className="flex items-center gap-2">
                    <span>STATUS:</span>
                    <span className={cn("px-1.5 py-0.5 rounded-sm font-bold", connected ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                        {connected ? 'LIVE' : 'DIS'}
                    </span>
                </div>
            </div>
        </header>

        {/* Workspace Layout: Resizable Panels */}
        <div className="flex-1 min-h-0 relative group">
            {mounted ? (
                <PanelGroup 
                    key={showAccountPanel ? 'expanded' : 'collapsed'} 
                    id={showAccountPanel ? 'mtf_layout_main_v4_expanded_auto' : 'mtf_layout_main_v4_collapsed_auto'}
                    orientation="vertical" 
                    className="h-full w-full"
                >
                    
                    {/* Top Area: Chart & Execution */}
                    <AnyPanel id="top-panel" defaultSize={70} minSize={15}>
                        <PanelGroup 
                            id="mtf_layout_order_v4_auto"
                            orientation="horizontal" 
                            className="h-full w-full"
                        >
                            
                            {/* Left: Chart */}
                            <AnyPanel id="chart-panel" defaultSize={75} minSize={15} className="relative">
                             {/* Toolbar (Moved inside Chart Panel) */}
                            <div className="absolute top-0 left-0 right-0 z-20 bg-gray-950/80 backdrop-blur-sm border-b border-white/5 p-2 px-4 flex justify-between items-center shrink-0">
                                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                                    {mounted ? availableTimeframes.map(tf => (
                                        <button
                                            key={tf}
                                            onClick={() => setTimeframe(tf)}
                                            className={cn(
                                                "px-2.5 py-1 rounded text-[10px] font-bold transition-all shrink-0",
                                                timeframe === tf 
                                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20" 
                                                    : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                                            )}
                                        >
                                            {tf}
                                        </button>
                                    )) : (
                                        DEFAULT_TIMEFRAMES.slice(0, 4).map(tf => (
                                            <div key={tf} className="px-3 py-1 rounded text-xs font-bold text-gray-700 bg-white/5">
                                                {tf}
                                            </div>
                                        ))
                                    )}
                                </div>

                                <div className="flex items-center gap-4 ml-4">
                                    <div className="flex items-center gap-1 bg-black/20 p-1 rounded-lg border border-white/5">
                                        {[
                                            { id: 'ADX', label: 'ADX', state: showADX, set: setShowADX },
                                            { id: 'EMA', label: 'EMA', state: showEMA, set: setShowEMA },
                                            { id: 'RSI', label: 'RSI', state: showRSI, set: setShowRSI },
                                            { id: 'MACD', label: 'MACD', state: showMACD, set: setShowMACD },
                                            { id: 'ATR', label: 'ATR', state: showATR, set: setShowATR },
                                            { id: 'SMC', label: 'SMC', state: showSMC, set: setShowSMC },
                                            { id: 'GMA', label: 'GAMMA', state: showGamma, set: setShowGamma },
                                        ].map(btn => (
                                            <button
                                                key={btn.id}
                                                onClick={() => btn.set(!btn.state)}
                                                className={cn(
                                                    "px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-colors",
                                                    btn.state ? "bg-white/10 text-white border border-white/10" : "text-gray-600 hover:text-gray-400"
                                                )}
                                            >
                                                {btn.label}
                                            </button>
                                        ))}
                                    </div>
                                    <button onClick={loadData} className="p-2 hover:bg-white/10 rounded-md text-gray-500 hover:text-white transition-colors">
                                        <RefreshCcw size={16} className={cn(loading && "animate-spin")} />
                                    </button>
                                </div>
                            </div>

                            {/* Chart Container */}
                            <div className="w-full h-full bg-gradient-to-b from-gray-900/50 to-black pt-12 cursor-crosshair active:cursor-grabbing">
                                 {candles.length > 0 ? (
                                    <ChartContainer>
                                        <CandleChart 
                                            data={candles} 
                                            indicators={chartIndicators.filter(i => i.priceScaleId !== 'left')} 
                                            colors={{
                                                backgroundColor: 'transparent',
                                                textColor: '#525252',
                                                upColor: '#3b82f6',     // Blue-500
                                                downColor: '#ffffff',   // White
                                                wickUpColor: '#3b82f6',
                                                wickDownColor: '#ffffff',
                                            }}
                                            rightOffset={25} 
                                            bid={prices[symbol]?.bid}
                                            ask={prices[symbol]?.ask}
                                            markers={smcMarkers}
                                            priceLines={[...smcPriceLines, ...orderLines, ...gammaPriceLines]}
                                            onLineDrag={handleLineDrag}
                                            precision={Number(getInstrument(symbol)?.details?.digits ?? getInstrument(symbol)?.details?.displayPrecision ?? 5)}
                                        />
                                        {chartIndicators.filter(i => i.priceScaleId === 'left').map(ind => {
                                            if (ind.name.startsWith('RSI')) {
                                                return (
                                                    <IndicatorChart 
                                                        key={ind.name}
                                                        type="RSI"
                                                        data={ind.data.map((v: number, i: number) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v as number || 0 }))}
                                                        height={100}
                                                        colors={{ lineColor: ind.color, textColor: '#525252' }}
                                                    />
                                                );
                                            }
                                            if (ind.name.startsWith('ATR')) {
                                                return (
                                                    <IndicatorChart 
                                                        key={ind.name}
                                                        type="ATR"
                                                        data={ind.data.map((v: number, i: number) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v as number || 0 }))}
                                                        height={100}
                                                        colors={{ lineColor: ind.color, textColor: '#525252' }}
                                                    />
                                                );
                                            }
                                            if (ind.name === 'MACD') {
                                                return (
                                                    <IndicatorChart 
                                                        key={ind.name}
                                                        type="MACD"
                                                        data={ind.data.map((v: { value: number; signal: number; hist: number }, i: number) => ({ 
                                                            time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, 
                                                            value: v.value,
                                                            signal: v.signal,
                                                            hist: v.hist
                                                        }))}
                                                        height={150}
                                                        colors={{ lineColor: '#2962FF', signalColor: '#FF6D00', histColor: '#26a69a', textColor: '#525252' }}
                                                    />
                                                );
                                            }
                                            if (ind.name.startsWith('ADX')) {
                                                return (
                                                    <IndicatorChart 
                                                        key={ind.name}
                                                        type="ADX"
                                                        data={ind.data.map((v: { value: number; dmp: number; dmn: number }, i: number) => ({ 
                                                            time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, 
                                                            value: v.value,
                                                            dmp: v.dmp,
                                                            dmn: v.dmn
                                                        }))}
                                                        height={100}
                                                        colors={{ lineColor: ind.color, textColor: '#525252' }}
                                                    />
                                                );
                                            }
                                            return null;
                                        })}
                                    </ChartContainer>
                                 ) : (
                                        <div className="flex items-center justify-center h-full text-gray-600 flex-col gap-3">
                                            {loading ? (
                                                <>
                                                    <RefreshCcw className="animate-spin text-blue-500" size={32} />
                                                    <span className="font-mono text-sm">Loading Market Data...</span>
                                                </>
                                            ) : (
                                                <span>Waiting for data...</span>
                                            )}
                                        </div>
                                 )}

                                 {/* Sentiment Overlay Overlay Toggle (Floating) */}
                                 <div className="absolute top-14 left-2 z-20">
                                    <button 
                                        onClick={() => setShowAnalytics(!showAnalytics)}
                                        className={cn("p-2 rounded bg-gray-900/80 backdrop-blur border border-white/10 hover:bg-gray-800 transition-colors", showAnalytics && "text-blue-400 border-blue-500/30")}
                                    >
                                        <Activity size={16} />
                                    </button>
                                 </div>
                            </div>
                        </AnyPanel>

                        <PanelResizeHandle className="relative z-50 group flex justify-center items-center bg-transparent w-4 -ml-2 hover:cursor-col-resize focus:outline-none">
                            <div className="w-px h-full bg-white/5 group-hover:bg-blue-500/50 transition-colors" />
                            <div className="absolute w-1 h-8 bg-white/10 rounded-full group-hover:bg-blue-500 transition-colors" />
                        </PanelResizeHandle>

                        <AnyPanel 
                            id="order-panel" 
                            ref={(node: any) => {
                                if (node) orderPanelRef.current = node;
                            }}
                            defaultSize={25} 
                            minSize={4} 
                            className="bg-gray-950"
                        >
                            <OrderPanel 
                                symbol={symbol} 
                                currentPrice={currentPrice} 
                                onOrderSuccess={handleOrderSuccess}
                                onOrderLinesChange={setOrderLines}
                                // Lifted State
                                slPrice={slPrice}
                                setSlPrice={setSlPrice}
                                tpPrice={tpPrice}
                                setTpPrice={setTpPrice}
                                limitPrice={limitPrice}
                                setLimitPrice={setLimitPrice}
                                slMode={slMode}
                                setSlMode={setSlMode}
                                tpMode={tpMode}
                                setTpMode={setTpMode}
                                onMinimize={() => {
                                    const panel = orderPanelRef.current;
                                    if (panel) {
                                        panel.resize(4);
                                    }
                                }}
                                onMaximize={() => {
                                    const panel = orderPanelRef.current;
                                    if (panel) {
                                        const size = panel.getSize();
                                        const currentSize = typeof size === 'number' ? size : (size as any).asPercentage;
                                        panel.resize(currentSize < 10 ? 25 : (currentSize > 30 ? 25 : 40));
                                    }
                                }}
                            />
                        </AnyPanel>

                    </PanelGroup>
                    </AnyPanel>
                    <PanelResizeHandle className="relative z-50 group flex justify-center items-center bg-transparent h-4 -mt-2 hover:cursor-row-resize focus:outline-none">
                        <div className="h-px w-full bg-white/5 group-hover:bg-blue-500/50 transition-colors" />
                        <div className="absolute h-1 w-16 bg-white/10 rounded-full group-hover:bg-blue-500 transition-colors" />
                    </PanelResizeHandle>
                    <AnyPanel 
                        id="account-panel"
                        ref={accountPanelRef}
                        defaultSize={30} 
                        minSize={4} 
                        collapsible={true}
                    >
                            <AccountPanel 
                            refreshTrigger={refreshTrigger}
                            onMinimize={() => {
                                const panel = accountPanelRef.current;
                                if (panel) {
                                    panel.resize(4);
                                }
                            }}
                            onMaximize={() => {
                                const panel = accountPanelRef.current;
                                if (panel) {
                                    const size = panel.getSize();
                                    const currentSize = typeof size === 'number' ? size : (size as any).asPercentage;
                                    panel.resize(currentSize < 10 ? 25 : (currentSize > 30 ? 25 : 40));
                                }
                            }}
                        />
                    </AnyPanel>
                </PanelGroup>
            ) : (
                <div className="h-full w-full bg-black animate-pulse" />
            )}
        </div>
        
        {/* Analytics Overlay (Absolute) */}
        {showAnalytics && (
             <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={() => setShowAnalytics(false)}>
                 <div className="w-full max-w-4xl bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
                      <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                          <h3 className="font-bold text-white">Market Sentiment Analysis</h3>
                          <button onClick={() => setShowAnalytics(false)} className="text-gray-500 hover:text-white">Close</button>
                      </div>
                      <div className="p-4 max-h-[80vh] overflow-y-auto">
                           <OpenInterestAnalytics />
                      </div>
                 </div>
             </div>
        )}

    </div>
  );
}
