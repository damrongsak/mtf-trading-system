"use client";

interface Step1Data {
  symbol: string;
  direction: string;
  session: string;
  entryPrice: string;
  stopLoss: string;
  takeProfit: string;
  riskAmount: string;
  exitPrice: string;
  pnl: string;
  contextScore: number;
}

interface Step1Props {
  data: Step1Data;
  onChange: (data: Step1Data) => void;
  onNext: () => void;
}

export default function Step1Technical({ data, onChange, onNext }: Step1Props) {
  const updateField = (field: keyof Step1Data, value: any) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-xl font-bold text-emerald-400 mb-4">Market Data (Forex)</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Pair</label>
            <select 
              value={data.symbol}
              onChange={(e) => updateField("symbol", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            >
              <option value="XAU/USD">XAU/USD</option>
              <option value="EUR/USD">EUR/USD</option>
              <option value="GBP/JPY">GBP/JPY</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Direction</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => updateField("direction", "LONG")}
                className={`flex-1 py-2 px-4 rounded font-medium transition-colors ${
                  data.direction === "LONG" 
                    ? "bg-emerald-500 text-gray-900" 
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                LONG
              </button>
              <button
                type="button"
                onClick={() => updateField("direction", "SHORT")}
                className={`flex-1 py-2 px-4 rounded font-medium transition-colors ${
                  data.direction === "SHORT" 
                    ? "bg-red-500 text-gray-900" 
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                SHORT
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Session</label>
            <select 
              value={data.session}
              onChange={(e) => updateField("session", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            >
              <option value="">Select...</option>
              <option value="Asian">Asian</option>
              <option value="London">London</option>
              <option value="NY">NY</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-xl font-bold text-emerald-400 mb-4">Risk & Money Management</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Entry Price</label>
            <input 
              type="number"
              step="0.01"
              value={data.entryPrice}
              onChange={(e) => updateField("entryPrice", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Stop Loss</label>
            <input 
              type="number"
              step="0.01"
              value={data.stopLoss}
              onChange={(e) => updateField("stopLoss", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Take Profit</label>
            <input 
              type="number"
              step="0.01"
              value={data.takeProfit}
              onChange={(e) => updateField("takeProfit", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Risk Amount ($)</label>
            <input 
              type="number"
              step="0.01"
              value={data.riskAmount}
              onChange={(e) => updateField("riskAmount", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-xl font-bold text-emerald-400 mb-4">Execution Result</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Exit Price</label>
            <input 
              type="number"
              step="0.01"
              value={data.exitPrice}
              onChange={(e) => updateField("exitPrice", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Realized P&L ($)</label>
            <input 
              type="number"
              step="0.01"
              value={data.pnl}
              onChange={(e) => updateField("pnl", e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Context Score: {data.contextScore}/10
          </label>
          <input 
            type="range"
            min="1"
            max="10"
            value={data.contextScore}
            onChange={(e) => updateField("contextScore", parseInt(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>
      </div>

      <button
        onClick={onNext}
        className="w-full py-3 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold rounded-lg transition-colors"
      >
        Next: Game Level →
      </button>
    </div>
  );
}
