
import React, { useState, useEffect, useRef } from 'react';
import { 
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart, ReferenceArea, Brush, Scatter
} from 'recharts';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Minimize2, Layers, Activity } from 'lucide-react';
import { GridLevel, PricePoint, BotConfig, OrderType, Trade, IndicatorType } from '../types';

interface MainChartProps {
  data: PricePoint[];
  gridLevels: GridLevel[];
  currentPrice: number;
  config: BotConfig;
  trades: Trade[];
}

export const MainChart: React.FC<MainChartProps> = ({ data, gridLevels, currentPrice, config, trades }) => {
  // --- STATE ---
  const [chartType, setChartType] = useState<'area' | 'line'>('area');
  const [scaleType, setScaleType] = useState<'linear' | 'log'>('linear');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Ref for fullscreen
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Zoom State
  const [zoomState, setZoomState] = useState<{ startIndex?: number; endIndex?: number }>({});

  // --- DATA PREP ---
  // Filter data to avoid scaling glitches when switching assets
  const relevantData = data.filter(d => {
      if (!currentPrice) return true;
      return d.price > currentPrice * 0.1 && d.price < currentPrice * 10;
  });

  const prices = relevantData.map(d => d.price);
  const bands = relevantData.flatMap(d => [d.upperBand, d.lowerBand]).filter((b): b is number => b !== undefined);
  const allValues = [...prices, ...bands, currentPrice, config.gridBottom, config.gridTop];
  
  const safeMin = Math.min(...allValues);
  const safeMax = Math.max(...allValues);
  
  // Dynamic Padding
  const range = safeMax - safeMin || (safeMin * 0.1); 
  const minPrice = Math.max(0.0001, safeMin - (range * 0.05)); // Log scale cant take <= 0
  const maxPrice = safeMax + (range * 0.05);

  // Trades & Positions
  const buyTrades = trades.filter(t => t.type === OrderType.BUY);
  const sellTrades = trades.filter(t => t.type === OrderType.SELL);
  
  // Derive Open Positions from Pending Sells (Inventory)
  const openPositions = gridLevels.filter(l => l.status === 'PENDING' && l.type === OrderType.SELL).map(l => ({
      price: l.price - ((config.gridTop - config.gridBottom)/config.gridCount), // Approx entry
      id: l.id
  }));

  // --- HANDLERS ---
  useEffect(() => { setZoomState({}); }, [config.assetSymbol]);
  useEffect(() => {
    if (relevantData.length <= 2) setZoomState({});
  }, [relevantData.length]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
        chartContainerRef.current?.requestFullscreen();
        setIsFullscreen(true);
    } else {
        if (document.fullscreenElement) {
             document.exitFullscreen();
        }
        setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleEsc = () => {
        if (!document.fullscreenElement) setIsFullscreen(false);
    };
    document.addEventListener('fullscreenchange', handleEsc);
    return () => document.removeEventListener('fullscreenchange', handleEsc);
  }, []);

  const formatPrice = (val: number) => {
      if (val < 1) return val.toFixed(5);
      if (val < 10) return val.toFixed(4);
      return val.toFixed(2);
  };

  const handleZoom = (direction: 'in' | 'out') => {
    const totalPoints = relevantData.length;
    if (totalPoints < 2) return;
    let start = zoomState.startIndex ?? 0;
    let end = zoomState.endIndex ?? totalPoints - 1;
    if (zoomState.startIndex === undefined) { start = 0; end = totalPoints - 1; }
    
    const currentRange = end - start;
    const zoomFactor = Math.max(1, Math.floor(currentRange * 0.25));

    if (direction === 'in') {
        if (currentRange <= 10) return;
        start += zoomFactor; end -= zoomFactor;
    } else {
        start -= zoomFactor; end += zoomFactor;
    }
    setZoomState({ startIndex: Math.max(0, start), endIndex: Math.min(totalPoints - 1, end) });
  };

  const indicatorColor = 
      config.activeIndicator === IndicatorType.BOLLINGER ? '#8b5cf6' :
      config.activeIndicator === IndicatorType.DONCHIAN ? '#f97316' :
      config.activeIndicator === IndicatorType.ATR_BANDS ? '#06b6d4' : 'transparent';

  return (
    <div 
        ref={chartContainerRef}
        className={`bg-[#0B0F19] border border-gray-800 rounded-sm relative overflow-hidden flex flex-col transition-all ${isFullscreen ? 'p-4' : 'h-[550px]'}`}
    >
      
      {/* --- TRADINGVIEW STYLE TOOLBAR --- */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#111827] z-20 shrink-0">
          <div className="flex items-center gap-4 overflow-x-auto">
              {/* Asset Info */}
              <div className="flex items-center gap-2 min-w-max">
                  <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-[10px]">
                      {config.assetSymbol ? config.assetSymbol.substring(0,1) : '$'}
                  </div>
                  <div>
                      <div className="text-white font-bold text-xs">{config.assetSymbol}USD</div>
                      <div className="text-[9px] text-gray-500">Perpetual • {config.simSpeed}ms Tick</div>
                  </div>
              </div>

              <div className="w-px h-6 bg-gray-700 hidden sm:block"></div>

              {/* Chart Controls */}
              <div className="flex bg-gray-800/50 rounded p-0.5 gap-0.5">
                  <button 
                    onClick={() => setChartType('area')}
                    className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-all ${chartType === 'area' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                  >
                    Area
                  </button>
                  <button 
                    onClick={() => setChartType('line')}
                    className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-all ${chartType === 'line' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                  >
                    Line
                  </button>
              </div>

              <button 
                onClick={() => setScaleType(s => s === 'linear' ? 'log' : 'linear')}
                className={`text-[10px] font-bold uppercase px-2 py-1 rounded transition-colors border ${scaleType === 'log' ? 'text-blue-400 bg-blue-900/20 border-blue-900/50' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
              >
                {scaleType === 'log' ? 'Log' : 'Lin'}
              </button>
              
               <button 
                onClick={() => setShowHeatmap(!showHeatmap)}
                className={`text-[10px] font-bold uppercase px-2 py-1 rounded transition-colors flex items-center gap-1 border ${showHeatmap ? 'text-orange-400 bg-orange-900/20 border-orange-900/50' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
              >
                <Layers size={10} /> Positions
              </button>
          </div>

          <div className="flex items-center gap-2 ml-4 shrink-0">
               {/* Quick Zoom */}
               <div className="flex bg-gray-800/50 rounded p-0.5 mr-2">
                    <button onClick={() => handleZoom('in')} className="p-1.5 text-gray-400 hover:text-blue-400" title="Zoom In"><ZoomIn size={14} /></button>
                    <button onClick={() => handleZoom('out')} className="p-1.5 text-gray-400 hover:text-blue-400" title="Zoom Out"><ZoomOut size={14} /></button>
                    <button onClick={() => setZoomState({})} className="p-1.5 text-gray-400 hover:text-red-400" title="Reset View"><RotateCcw size={14} /></button>
               </div>
               <button onClick={toggleFullscreen} className="text-gray-400 hover:text-white p-1" title="Fullscreen">
                   {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
               </button>
          </div>
      </div>

      <div className="flex-1 relative w-full min-h-0 bg-[#0B0F19]">
        <ResponsiveContainer width="100%" height="100%">
            <ComposedChart 
                data={relevantData} 
                margin={{ top: 20, right: 60, left: 10, bottom: 5 }}
            >
            <defs>
                <linearGradient id="gridZoneGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.05}/>
                    <stop offset="50%" stopColor="#3b82f6" stopOpacity={0.15}/>
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
            </defs>
            
            <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="#1f2937" 
                vertical={true} 
                horizontal={true}
                opacity={0.2} 
            />
            
            <XAxis 
                dataKey="timestamp" 
                type="number" 
                domain={['dataMin', 'dataMax']} 
                tickFormatter={(unixTime) => new Date(unixTime).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}
                stroke="#374151"
                tick={{fontSize: 10, fontFamily: 'monospace', fill: '#6b7280'}}
                minTickGap={60}
                axisLine={false}
                tickLine={false}
                height={30}
            />
            
            <YAxis 
                domain={[minPrice, maxPrice]} 
                scale={scaleType}
                orientation="right" 
                stroke="#4b5563"
                tickFormatter={formatPrice}
                tick={{fontSize: 10, fontFamily: 'monospace', fill: '#6b7280'}}
                axisLine={false}
                tickLine={false}
                width={60}
            />
            
            <Tooltip 
                contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#fff', fontSize: '12px', borderRadius: '4px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)' }}
                itemStyle={{ color: '#60a5fa' }}
                cursor={{ stroke: '#9ca3af', strokeWidth: 1, strokeDasharray: '4 4' }} // Crosshair
                formatter={(value: number, name: string) => {
                    if (name === 'upperBand' || name === 'lowerBand') return [formatPrice(value), config.activeIndicator];
                    return [formatPrice(value), name === 'price' ? 'Price' : name];
                }}
                labelFormatter={(label) => new Date(label).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            />
            
            {/* Active Grid Zone */}
            <ReferenceArea 
                y1={config.gridBottom} 
                y2={config.gridTop} 
                fill="url(#gridZoneGradient)"
            />

            {/* HEATMAP / POSITIONS */}
            {showHeatmap && openPositions.map((pos) => (
                <ReferenceLine 
                    key={`pos-${pos.id}`}
                    y={pos.price}
                    stroke="#f97316"
                    strokeWidth={1}
                    strokeOpacity={0.4}
                />
            ))}

            {/* PENDING ORDERS (TradingView Style Badges) */}
            {gridLevels.map((level) => {
                if (level.status !== 'PENDING') return null;
                const isBuy = level.type === OrderType.BUY;
                // Only show labels for levels close to current price to reduce clutter
                const isClose = currentPrice > 0 && Math.abs(level.price - currentPrice) / currentPrice < 0.05; 
                
                return (
                    <ReferenceLine 
                        key={level.id}
                        y={level.price}
                        stroke={isBuy ? '#10b981' : '#ef4444'}
                        strokeDasharray="2 2"
                        strokeOpacity={0.3}
                        strokeWidth={1}
                        // Use Custom label prop logic if simple string
                        label={isClose ? { 
                            position: 'right', 
                            fill: isBuy ? '#10b981' : '#ef4444',
                            fontSize: 9,
                            value: formatPrice(level.price),
                            className: "font-mono font-bold"
                        } : undefined}
                    />
                );
            })}

            {/* LIMITS */}
            <ReferenceLine y={config.maxBuyPrice} stroke="#10b981" strokeDasharray="5 5" strokeWidth={1} label={{ value: 'MAX BUY', position: 'insideRight', fill: '#10b981', fontSize: 10, dy: -10 }} />
            <ReferenceLine y={config.minSellPrice} stroke="#ef4444" strokeDasharray="5 5" strokeWidth={1} label={{ value: 'MIN SELL', position: 'insideRight', fill: '#ef4444', fontSize: 10, dy: 10 }} />
            
            {/* MARKET PRICE LINE */}
            <ReferenceLine 
                y={currentPrice} 
                stroke="#ffffff" 
                strokeDasharray="2 2" 
                strokeWidth={1} 
                label={{ 
                    position: 'right', 
                    fill: '#3b82f6', 
                    fontSize: 11,
                    fontWeight: 'bold',
                    value: `MARKET`,
                    dy: -15
                }}
            />

            {/* INDICATORS */}
            {config.activeIndicator !== IndicatorType.NONE && (
                <>
                    <Line type="monotone" dataKey="upperBand" stroke={indicatorColor} strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="lowerBand" stroke={indicatorColor} strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
                </>
            )}
            
            {/* MAIN CHART */}
            {chartType === 'area' ? (
                <Area 
                    type="monotone" 
                    dataKey="price" 
                    stroke="#3b82f6" 
                    fill="url(#areaGradient)" 
                    strokeWidth={2}
                    isAnimationActive={false} 
                />
            ) : (
                <Line 
                    type="monotone" 
                    dataKey="price" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false} 
                />
            )}

            {/* EXECUTIONS */}
            <Scatter name="Buy" data={buyTrades} fill="#10b981" shape="triangle" legendType="none" />
            <Scatter 
                name="Sell" 
                data={sellTrades} 
                fill="#ef4444" 
                shape={(props: any) => {
                    const { cx, cy, fill } = props;
                    return <path d={`M${cx - 4},${cy - 4}L${cx + 4},${cy - 4}L${cx},${cy + 4}Z`} fill={fill} />;
                }}
                legendType="none"
            />

            <Brush 
                dataKey="timestamp"
                height={20}
                stroke="#4b5563"
                fill="#0B0F19"
                tickFormatter={() => ''} 
                travellerWidth={6}
                alwaysShowText={false}
                startIndex={zoomState.startIndex}
                endIndex={zoomState.endIndex}
                onChange={(e: any) => {
                    if (e.startIndex !== undefined && e.endIndex !== undefined) {
                        const isFullRange = e.startIndex === 0 && e.endIndex === relevantData.length - 1;
                        const isAtEdge = e.endIndex >= relevantData.length - 2;
                        if (isFullRange || isAtEdge) {
                            if (zoomState.startIndex !== undefined) setZoomState({});
                        } else {
                            if (e.startIndex !== zoomState.startIndex || e.endIndex !== zoomState.endIndex) {
                                setZoomState({ startIndex: e.startIndex, endIndex: e.endIndex });
                            }
                        }
                    }
                }}
            />

            </ComposedChart>
        </ResponsiveContainer>

        {/* HUD OVERLAY - Always Visible but smaller */}
        <div className="absolute top-4 left-4 z-10 flex gap-4 pointer-events-none">
             {/* Small Equity Sparkline */}
             <div className="bg-black/20 backdrop-blur-sm p-2 rounded border border-white/5">
                <h3 className="text-gray-500 font-bold text-[9px] uppercase tracking-widest mb-1 flex items-center gap-1">
                    <Activity size={10} className="text-red-400" /> Equity
                </h3>
                <div className="h-10 w-24">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={relevantData}>
                            <Area type="monotone" dataKey="equity" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} strokeWidth={1} isAnimationActive={false} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
             </div>
        </div>

      </div>
    </div>
  );
};
