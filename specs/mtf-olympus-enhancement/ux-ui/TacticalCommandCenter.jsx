import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, 
  Target, 
  Activity, 
  Zap, 
  CheckCircle, 
  XCircle, 
  MessageSquare,
  Crosshair,
  History,
  Brain,
  Volume2,
  Image as ImageIcon,
  Loader2,
  Mic2,
  TrendingUp,
  Map as MapIcon,
  Maximize2
} from 'lucide-react';

// Note: apiKey will be provided by the execution environment
const apiKey = "";

const App = () => {
  // --- 1. Tactical State (State Vector) ---
  const [marketState, setMarketState] = useState({
    timestamp: new Date().toISOString(),
    price_close: 2685.42,
    adx_strength: 18.5,
    atr_volatility: 12.3,
    volume_status: "High Activity",
    market_session: "New York",
    fib_0_618: 2672.15,
    smc_structure: "BoS Bullish Detected",
    order_block: "M15 Bullish OB @ 2675.00"
  });

  const [aiProposal] = useState({
    zone_type: "Killing Zone",
    action: "DEPLOY BUY GRID",
    range_low: 2672.00,
    range_high: 2682.00,
    rationale: "Price rejected the 0.618 Fib level within a Bullish Order Block at M15 structure. NY session volume is surging, providing sufficient liquidity.",
    risk_level: "Medium",
    expected_yield: "1.2% - 1.8%"
  });

  // --- 2. Chart Integration (TradingView Lightweight Charts) ---
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const [libLoaded, setLibLoaded] = useState(false);

  // Inject Lightweight Charts Library
  useEffect(() => {
    const script = document.createElement('script');
    script.src = "https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js";
    script.async = true;
    script.onload = () => setLibLoaded(true);
    document.head.appendChild(script);
    return () => { if (document.head.contains(script)) document.head.removeChild(script); };
  }, []);

  // Initialize Chart
  useEffect(() => {
    if (!libLoaded || !chartContainerRef.current) return;
    if (!window.LightweightCharts) return;

    const chart = window.LightweightCharts.createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: 'rgba(30, 41, 59, 0.3)' }, horzLines: { color: 'rgba(30, 41, 59, 0.3)' } },
      crosshair: { mode: window.LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(30, 41, 59, 0.8)', visible: true },
      timeScale: { borderColor: 'rgba(30, 41, 59, 0.8)', timeVisible: true, secondsVisible: false },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#f24968', borderVisible: false,
      wickUpColor: '#10b981', wickDownColor: '#f24968',
    });

    // Generate Initial Data
    let currentPrice = 2675;
    const initialData = [];
    const now = Math.floor(Date.now() / 1000);
    for (let i = 0; i < 100; i++) {
      const open = currentPrice + (Math.random() - 0.5) * 4;
      const close = open + (Math.random() - 0.48) * 6;
      const high = Math.max(open, close) + Math.random() * 2;
      const low = Math.min(open, close) - Math.random() * 2;
      initialData.push({ time: now - (100 - i) * 900, open, high, low, close });
      currentPrice = close;
    }
    candlestickSeries.setData(initialData);

    // Tactical Lines
    candlestickSeries.createPriceLine({ price: aiProposal.range_high, color: '#f97316', lineWidth: 2, lineStyle: window.LightweightCharts.LineStyle.Dashed, title: 'ZONE HIGH' });
    candlestickSeries.createPriceLine({ price: aiProposal.range_low, color: '#f97316', lineWidth: 2, lineStyle: window.LightweightCharts.LineStyle.Dashed, title: 'ZONE LOW' });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;

    const interval = setInterval(() => {
      if (!candlestickSeriesRef.current) return;
      const lastData = initialData[initialData.length - 1];
      const nextOpen = lastData.close;
      const nextClose = nextOpen + (Math.random() - 0.48) * 4;
      const nextHigh = Math.max(nextOpen, nextClose) + Math.random() * 1.5;
      const nextLow = Math.min(nextOpen, nextClose) - Math.random() * 1.5;
      const nextBar = { time: lastData.time + 900, open: nextOpen, high: nextHigh, low: nextLow, close: nextClose };
      candlestickSeriesRef.current.update(nextBar);
      initialData.push(nextBar);
      setMarketState(ms => ({...ms, price_close: nextBar.close}));
    }, 5000);

    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);

    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [libLoaded, aiProposal.range_high, aiProposal.range_low]);

  // --- 3. Interaction States ---
  const [commanderNote, setCommanderNote] = useState("");
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [aiInsight, setAiInsight] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [isGeneratingImg, setIsGeneratingImg] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // PCM-to-WAV Utility
  const pcmToWav = (pcmData, sampleRate) => {
    const buffer = new ArrayBuffer(44 + pcmData.length * 2);
    const view = new DataView(buffer);
    const writeString = (o, str) => { for (let i = 0; i < str.length; i++) view.setUint8(o + i, str.charCodeAt(i)); };
    writeString(0, 'RIFF'); view.setUint32(4, 32 + pcmData.length * 2, true);
    writeString(8, 'WAVE'); writeString(12, 'fmt '); view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    writeString(36, 'data'); view.setUint32(40, pcmData.length * 2, true);
    for (let i = 0; i < pcmData.length; i++) view.setInt16(44 + i * 2, pcmData[i], true);
    return buffer;
  };

  const fetchWithRetry = async (url, options, retries = 5, backoff = 1000) => {
    try {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      if (retries > 0) {
        await new Promise(r => setTimeout(r, backoff));
        return fetchWithRetry(url, options, retries - 1, backoff * 2);
      }
      throw error;
    }
  };

  const analyzeBattlefield = async () => {
    setIsAnalyzing(true); setAiInsight("");
    try {
      const result = await fetchWithRetry(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: `XAU Price: ${marketState.price_close}, SMC: ${marketState.smc_structure}. Analyze tactical risk for ${aiProposal.action}.` }] }] })
      });
      setAiInsight(result.candidates?.[0]?.content?.parts?.[0]?.text || "No intelligence.");
    } catch { setAiInsight("Comms Down."); } finally { setIsAnalyzing(false); }
  };

  const visualizeBattlefield = async () => {
    setIsGeneratingImg(true);
    try {
      const result = await fetchWithRetry(`https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${apiKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instances: { prompt: "Futuristic trading HUD, golden candlesticks, glowing grid, 8k" }, parameters: { sampleCount: 1 } })
      });
      if (result.predictions?.[0]?.bytesBase64Encoded) setGeneratedImage(`data:image/png;base64,${result.predictions[0].bytesBase64Encoded}`);
    } catch (e) { console.error(e); } finally { setIsGeneratingImg(false); }
  };

  const playVoiceBriefing = async () => {
    if (isSpeaking) return; setIsSpeaking(true);
    try {
      const text = `Tactical update: Market is ${marketState.smc_structure}. Current price ${marketState.price_close.toFixed(2)}. Briefing: ${aiInsight || aiProposal.rationale}`;
      const result = await fetchWithRetry(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${apiKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: `Speak firmly: ${text}` }] }],
          generationConfig: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } } } }
        })
      });
      const audioB64 = result.candidates[0].content.parts[0].inlineData.data;
      const audioContent = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0));
      const wavBuffer = pcmToWav(new Int16Array(audioContent.buffer), 24000);
      const audioUrl = URL.createObjectURL(new Blob([wavBuffer], { type: 'audio/wav' }));
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsSpeaking(false);
      audio.play();
    } catch { setIsSpeaking(false); }
  };

  const handleDecision = (decision) => {
    setIsProcessing(true);
    const entry = { engagement_id: `TX-${Math.random().toString(36).substr(2, 6).toUpperCase()}`, state: marketState, human_decision: { action: decision, note: commanderNote, timestamp: new Date().toISOString() } };
    setTimeout(() => { setLogs(prev => [entry, ...prev]); setCommanderNote(""); setIsProcessing(false); }, 1000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans p-4 md:p-8 selection:bg-blue-500/30">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-slate-800 pb-6 gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-blue-400 flex items-center gap-3"><Shield className="w-10 h-10" /> OLYMPUS TACTICAL</h1>
          <p className="text-slate-500 text-xs uppercase tracking-[0.3em] mt-2 font-bold font-mono">GOLD CONQUEST v1.6.5</p>
        </div>
        <div className="flex gap-8 text-sm bg-slate-900/50 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
          <div className="flex flex-col items-end"><span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Session</span><span className="text-emerald-400 font-mono font-black">{marketState.market_session.toUpperCase()}</span></div>
          <div className="flex flex-col items-end border-l border-slate-800 pl-8 font-mono"><span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Timeframe</span><span className="text-blue-400 font-black">15M</span></div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="space-y-6 lg:col-span-1">
          <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-sm">
            <h2 className="text-[10px] font-black text-slate-500 mb-6 flex items-center gap-2 tracking-[0.2em] uppercase"><Activity className="w-4 h-4 text-blue-500" /> Sensors</h2>
            <div className="space-y-4 font-mono">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 hover:border-emerald-500/30 transition-all group">
                <p className="text-[10px] text-slate-500 mb-1 font-bold">ADX</p>
                <div className="flex items-end gap-2"><span className="text-2xl font-black">{marketState.adx_strength}</span><span className="text-[10px] text-emerald-500 font-bold mb-1">STATIONARY</span></div>
                <div className="w-full bg-slate-800 h-1 mt-3 rounded-full overflow-hidden"><div className="bg-emerald-500 h-full shadow-[0_0_12px_rgba(16,185,129,0.8)]" style={{width: `${marketState.adx_strength * 2}%`}}></div></div>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 hover:border-white/20 transition-all"><p className="text-[10px] text-slate-500 mb-1 font-bold uppercase">XAU/USD SPOT</p><span className="text-2xl font-black text-white">${marketState.price_close.toFixed(2)}</span></div>
            </div>
          </section>
          <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-sm">
            <h2 className="text-[10px] font-black text-red-400 mb-6 flex items-center gap-2 tracking-[0.2em] uppercase"><Target className="w-4 h-4" /> SMC Intel</h2>
            <div className="space-y-3 font-mono">
              <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border-l-4 border-emerald-500 shadow-inner"><span className="text-[10px] text-slate-500 font-bold">BIAS</span><span className="text-xs font-black text-emerald-400 uppercase">M15 Bullish</span></div>
              <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border-l-4 border-blue-500 shadow-inner"><span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">POI</span><span className="text-xs font-black text-blue-400 uppercase">Order Block</span></div>
            </div>
          </section>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <section className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl flex flex-col h-[480px]">
             <div className="p-4 bg-slate-900/80 border-b border-slate-800 flex justify-between items-center px-8">
               <div className="flex items-center gap-3"><TrendingUp className="w-5 h-5 text-blue-500" /><h2 className="text-lg font-black text-white tracking-tight uppercase">Battlefield Commander <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded ml-2 uppercase">LIVE M15</span></h2></div>
               <div className="flex gap-4 font-mono text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                 <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-[#10b981]"></div> Bull</div>
                 <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-[#f24968]"></div> Bear</div>
               </div>
             </div>
             <div className="flex-grow w-full bg-slate-950 relative" ref={chartContainerRef}>{!libLoaded && <div className="absolute inset-0 flex items-center justify-center bg-slate-950"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>}</div>
          </section>

          <div className="bg-blue-600/5 border border-blue-500/20 rounded-3xl p-8 relative overflow-hidden shadow-2xl backdrop-blur-md">
            <div className="flex flex-col md:flex-row items-center gap-6 mb-8 border-b border-blue-500/10 pb-6">
              <div className="p-4 bg-blue-500 rounded-2xl text-white shadow-lg shadow-blue-500/20"><Zap className="w-8 h-8" /></div>
              <div className="flex-grow">
                <h2 className="text-2xl font-black text-white italic tracking-tight uppercase">Strategic Proposal</h2>
                <p className="text-slate-500 text-[10px] font-mono uppercase font-bold tracking-widest mt-1">General Intelligence Agent</p>
              </div>
              <div className="flex gap-3">
                <button onClick={analyzeBattlefield} className="px-4 py-2 bg-slate-900 border border-blue-500/30 text-blue-400 rounded-xl text-xs font-bold flex items-center gap-2 hover:bg-blue-500/10 transition-all">{isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />} INSIGHT</button>
                <button onClick={playVoiceBriefing} disabled={isSpeaking} className="px-4 py-2 bg-slate-900 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-bold flex items-center gap-2 hover:bg-emerald-500/10 transition-all disabled:opacity-50">{isSpeaking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Volume2 className="w-4 h-4" />} BRIEFING</button>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-10 mb-8">
              <div className="space-y-6">
                <div><label className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Objective</label><p className="text-3xl font-black text-white italic tracking-tighter mt-1">{aiProposal.action}</p></div>
                <div className="flex gap-12 font-mono">
                  <div><label className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Target</label><p className="text-xl font-black text-blue-400 tracking-tighter">${aiProposal.range_low}-${aiProposal.range_high}</p></div>
                  <div><label className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Risk</label><p className="text-xl font-black text-orange-500 uppercase">{aiProposal.risk_level}</p></div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800/50 italic text-slate-300 text-sm leading-relaxed min-h-[100px] shadow-inner relative"><div className="absolute -top-3 -left-2 p-1.5 bg-blue-500 rounded-lg shadow-lg"><MessageSquare className="w-3 h-3 text-white fill-current" /></div>{aiInsight || aiProposal.rationale}</div>
                <button onClick={visualizeBattlefield} className="w-full py-2 bg-slate-900 border border-slate-800 rounded-xl text-[10px] font-black text-slate-500 hover:text-blue-400 transition-all uppercase tracking-widest flex items-center justify-center gap-2">{isGeneratingImg ? <Loader2 className="w-3 h-3 animate-spin" /> : <ImageIcon className="w-3 h-3" />} HUD RENDER</button>
              </div>
            </div>

            {generatedImage && (
              <div className="mb-8 rounded-3xl overflow-hidden border border-blue-500/20 shadow-2xl relative group h-56 bg-slate-900">
                <img src={generatedImage} alt="Battlefield" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent"></div>
                <button onClick={() => setGeneratedImage(null)} className="absolute top-4 right-4 p-2 bg-black/60 rounded-full hover:bg-red-500 transition-all"><XCircle className="w-5 h-5 text-white" /></button>
              </div>
            )}

            <div className="space-y-6">
              <textarea value={commanderNote} onChange={(e) => setCommanderNote(e.target.value)} placeholder="Analyze M15 structure and label for LSTM training..." className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-6 text-sm text-slate-300 focus:ring-2 focus:ring-blue-500 transition-all min-h-[120px] shadow-inner font-mono" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
                <button onClick={() => handleDecision("REJECT")} className="flex items-center justify-center gap-2 py-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition-all font-black text-xs uppercase tracking-widest"><XCircle className="w-5 h-5" /> Abort</button>
                <button onClick={() => handleDecision("MODIFY")} className="flex items-center justify-center gap-2 py-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 hover:bg-blue-500/10 hover:text-blue-400 transition-all font-black text-xs uppercase tracking-widest"><Activity className="w-5 h-5" /> Adjust</button>
                <button onClick={() => handleDecision("APPROVE")} disabled={isProcessing} className={`flex items-center justify-center gap-2 py-5 rounded-2xl font-black text-xs transition-all uppercase tracking-widest shadow-xl ${isProcessing ? 'bg-slate-800' : 'bg-blue-500 text-white shadow-blue-500/30'}`}>{isProcessing ? <span className="animate-pulse">Processing...</span> : <><CheckCircle className="w-5 h-5" /> Engage</>}</button>
              </div>
            </div>
          </div>

          <section className="bg-slate-900/30 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl backdrop-blur-sm">
            <div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center px-8">
              <h2 className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase flex items-center gap-2"><History className="w-4 h-4 text-blue-500" /> Engagement History</h2>
              <span className="text-[10px] text-slate-600 font-bold uppercase font-mono">LSTM_DATASET_READY</span>
            </div>
            <div className="max-h-[350px] overflow-y-auto divide-y divide-slate-800/50 font-mono">
              {logs.length === 0 ? <div className="p-16 text-center text-slate-700 italic text-sm tracking-widest uppercase opacity-30">Waiting for deployment...</div> : logs.map((log, i) => (
                <div key={i} className="p-6 hover:bg-slate-800/20 transition-all px-8 group">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex gap-4 items-center"><span className="text-blue-500 text-xs font-bold bg-blue-500/10 px-2 py-1 rounded">#{log.engagement_id}</span><span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${log.human_decision.action === 'APPROVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>{log.human_decision.action}</span></div>
                    <span className="text-[10px] text-slate-600">{new Date(log.human_decision.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-sm text-slate-300 italic group-hover:text-white transition-colors">{log.human_decision.note || "No situational notes."}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      <footer className="mt-12 flex justify-between items-center text-[10px] text-slate-700 uppercase tracking-[0.4em] border-t border-slate-900 pt-8 font-mono">
        <div className="flex gap-8 font-black"><span className="flex items-center gap-2"><Zap className="w-3 h-3 text-blue-500 shadow-lg" /> Latency: 12ms</span><span className="flex items-center gap-2 text-emerald-600"><CheckCircle className="w-3 h-3" /> M15 Real-time Engine Linked</span></div>
        <span className="font-black hover:text-blue-500 transition-colors underline decoration-blue-500/20 underline-offset-4">Olympus MTF - Gold Conquest OS v1.6.5</span>
      </footer>
    </div>
  );
};

export default App;