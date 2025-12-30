import React from 'react';

interface SignalCardProps {
  symbol: string;
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  timeframe: string;
  confidence: number;
  timestamp: string;
  reason?: string;
  reasoning?: string;
  entry_price?: number;
  sl_price?: number;
  tp_price?: number;
  broker?: string;
}

export const SignalCard: React.FC<SignalCardProps> = (props) => {
  const {
      symbol,
      direction,
      timestamp,
      confidence,
      timeframe,
      broker
  } = props;
  const isBullish = direction === 'BULLISH';
  const isBearish = direction === 'BEARISH';
  
  const borderColor = isBullish 
    ? 'border-accent-green/30' 
    : isBearish 
      ? 'border-accent-red/30' 
      : 'border-gray-700';

  const glowColor = isBullish
    ? 'shadow-[0_0_20px_-5px_rgba(16,185,129,0.2)]'
    : isBearish
      ? 'shadow-[0_0_20px_-5px_rgba(239,68,68,0.2)]'
      : '';

  const textColor = isBullish
    ? 'text-accent-green'
    : isBearish
      ? 'text-accent-red'
      : 'text-gray-400';

  return (
    <div className={`
      relative overflow-hidden rounded-xl border ${borderColor} 
      bg-gray-850/50 backdrop-blur-sm p-5
      transition-all duration-300 hover:scale-[1.02]
      ${glowColor}
    `}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-gray-100 tracking-tight">{symbol}</h3>
            {broker && (
              <span className="px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                {broker}
              </span>
            )}
          </div>
          <span className="text-xs font-mono text-gray-500">{timeframe}</span>
        </div>
        <div className={`
          px-3 py-1 rounded-full text-xs font-bold tracking-wider
          ${isBullish ? 'bg-accent-green/10 text-accent-green border border-accent-green/20' : ''}
          ${isBearish ? 'bg-accent-red/10 text-accent-red border border-accent-red/20' : ''}
          ${!isBullish && !isBearish ? 'bg-gray-700/50 text-gray-400' : ''}
        `}>
          {direction}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500">Confidence</span>
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${isBullish ? 'bg-accent-green' : isBearish ? 'bg-accent-red' : 'bg-gray-500'}`}
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className={`text-sm font-mono font-bold ${textColor}`}>
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        <div className="pt-3 border-t border-gray-800">
            {/* Price Levels (New) */}
            <div className="grid grid-cols-3 gap-2 mb-3 text-xs font-mono">
                <div className="text-gray-500">
                    Entry: <span className="text-gray-300">{props.entry_price ? Number(props.entry_price).toFixed(5) : '-'}</span>
                </div>
                <div className="text-gray-500 text-center">
                    TP: <span className="text-accent-green">{props.tp_price ? Number(props.tp_price).toFixed(5) : '-'}</span>
                </div>
                <div className="text-gray-500 text-right">
                    SL: <span className="text-accent-red">{props.sl_price ? Number(props.sl_price).toFixed(5) : '-'}</span>
                </div>
            </div>

           <p className="text-sm text-gray-400 line-clamp-2">
             {props.reason || props.reasoning || "No reasoning provided."}
           </p>
           <p className="text-xs text-gray-600 mt-2 font-mono text-right">
             {new Date(timestamp).toLocaleTimeString()}
           </p>
        </div>
      </div>
    </div>
  );
};
