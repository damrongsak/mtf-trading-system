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

    // Inject Lightweight Charts Library with specific version for stability
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

        // Safety check for global object
        if (!window.LightweightCharts) return;

        // Create Chart Instance
        const chart = window.LightweightCharts.createChart(chartContainerRef.current, {
            layout: {
                background: { color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(30, 41, 59, 0.3)' },
                horzLines: { color: 'rgba(30, 41, 59, 0.3)' },
            },
            crosshair: {
                mode: window.LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: 'rgba(30, 41, 59, 0.8)',
                visible: true,
            },
            timeScale: {
                borderColor: 'rgba(30, 41, 59, 0.8)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Add Candlestick Series
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10b981',
            downColor: '#f24968',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#f24968',
        });

        // Generate Initial Data (M15 Gold Simulation)
        let currentPrice = 2675;
        const initialData = [];
        const now = Math.floor(Date.now() / 1000);
        for (let i = 0; i < 100; i++) {
            const open = currentPrice + (Math.random() - 0.5) * 4;
            const close = open + (Math.random() - 0.48) * 6;
            const high = Math.max(open, close) + Math.random() * 2;
            const low = Math.min(open, close) - Math.random() * 2;

            initialData.push({
                time: now - (100 - i) * 900,
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2)),
            });
            currentPrice = close;
        }
        candlestickSeries.setData(initialData);

        // Add Tactical Zones (Price Lines)
        candlestickSeries.createPriceLine({
            price: aiProposal.range_high,
            color: '#f97316',
            lineWidth: 2,
            lineStyle: window.LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'ZONE HIGH',
        });
        candlestickSeries.createPriceLine({
            price: aiProposal.range_low,
            color: '#f97316',
            lineWidth: 2,
            lineStyle: window.LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'ZONE LOW',
        });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;

        // Simulation Loop for Live Updates
        const interval = setInterval(() => {
            if (!candlestickSeriesRef.current) return;

            const lastData = initialData[initialData.length - 1];
            const nextOpen = lastData.close;
            const nextClose = nextOpen + (Math.random() - 0.48) * 4;
            const nextHigh = Math.max(nextOpen, nextClose) + Math.random() * 1.5;
            const nextLow = Math.min(nextOpen, nextClose) - Math.random() * 1.5;

            const nextBar = {
                time: lastData.time + 900,
                open: parseFloat(nextOpen.toFixed(2)),
                high: parseFloat(nextHigh.toFixed(2)),
                low: parseFloat(nextLow.toFixed(2)),
                close: parseFloat(nextClose.toFixed(2)),
            };

            candlestickSeriesRef.current.update(nextBar);
            initialData.push(nextBar);
            setMarketState(ms => ({ ...ms, price_close: nextBar.close }));
        }, 5000);

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            clearInterval(interval);
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [libLoaded, aiProposal.range_high, aiProposal.range_low]);

    // --- 3. AI & Interaction States ---
    const [commanderNote, setCommanderNote] = useState("");
    const [logs, setLogs] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [aiInsight, setAiInsight] = useState("");
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [generatedImage, setGeneratedImage] = useState(null);
    const [isGeneratingImg, setIsGeneratingImg] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);

    // Exponential Backoff Utility
    const fetchWithRetry = async (url, options, retries = 5, backoff = 1000) => {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            if (retries > 0) {
                await new Promise(resolve => setTimeout(resolve, backoff));
                return fetchWithRetry(url, options, retries - 1, backoff * 2);
            }
            throw error;
        }
    };

    const analyzeBattlefield = async () => {
        setIsAnalyzing(true);
        setAiInsight("");
        try {
            const prompt = `Gold M15 Chart Analysis. Current Price: ${marketState.price_close}, Structure: ${marketState.smc_structure}, Session: ${marketState.market_session}. Advise on deploying Grid strategy in the Killing Zone at ${aiProposal.range_low}-${aiProposal.range_high}.`;
            const result = await fetchWithRetry(
                `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
                }
            );
            setAiInsight(result.candidates?.[0]?.content?.parts?.[0]?.text || "Tactical data unavailable.");
        } catch { setAiInsight("Comms Failure: Signal lost."); }
        finally { setIsAnalyzing(false); }
    };

    const visualizeBattlefield = async () => {
        setIsGeneratingImg(true);
        try {
            const prompt = `Professional trading HUD visualization, 15-minute Gold candlesticks, glowing holographic tactical zones, high-tech military interface.`;
            const result = await fetchWithRetry(
                `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${apiKey}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ instances: { prompt: prompt }, parameters: { sampleCount: 1 } })
                }
            );
            if (result.predictions?.[0]?.bytesBase64Encoded) {
                setGeneratedImage(`data:image/png;base64,${result.predictions[0].bytesBase64Encoded}`);
            }
        } catch (e) { console.error("Imagen Error:", e); }
        finally { setIsGeneratingImg(false); }
    };

    const playVoiceBriefing = async () => {
        if (isSpeaking) return;
        setIsSpeaking(true);
        try {
            const text = `Commander, battlefield update for ${marketState.market_session}. Current gold price is ${marketState.price_close}. Deployment in the killing zone is advised based on recent structure shift.`;
            const result = await fetchWithRetry(
                `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${apiKey}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        contents: [{ parts: [{ text: `Speak firmly: ${text}` }] }],
                        generationConfig: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } } } }
                    })
                }
            );
            const audioB64 = result.candidates[0].content.parts[0].inlineData.data;
            const audio = new Audio(`data:audio/wav;base64,${audioB64}`);
            audio.onended = () => setIsSpeaking(false);
            audio.play();
        } catch { setIsSpeaking(false); }
    };

    const handleDecision = (decision) => {
        setIsProcessing(true);
        const entry = {
            engagement_id: `TX-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
            state: marketState,
            human_decision: { action: decision, note: commanderNote, timestamp: new Date().toISOString() }
        };
        setTimeout(() => {
            setLogs(prev => [entry, ...prev]);
            setCommanderNote("");
            setIsProcessing(false);
        }, 1200);
    };

    return (
        <div className= "min-h-screen bg-slate-950 text-slate-200 font-sans p-4 md:p-8 selection:bg-blue-500/30" >
        {/* HUD Header */ }
        < header className = "flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-slate-800 pb-6 gap-4" >
            <div>
            <h1 className="text-3xl font-black tracking-tighter text-blue-400 flex items-center gap-3" >
                <Shield className="w-10 h-10" /> OLYMPUS TACTICAL COMMAND
                    </h1>
                    < p className = "text-slate-500 text-xs uppercase tracking-[0.3em] mt-2 font-bold flex items-center gap-2 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 font-mono" >
                        <Maximize2 className="w-3 h-3 text-blue-400" /> OPERATION: GOLD CONQUEST v1.6.4
                            </p>
                            </div>
                            < div className = "flex gap-8 text-sm bg-slate-900/50 p-4 rounded-2xl border border-slate-800 backdrop-blur-md shadow-inner" >
                                <div className="flex flex-col items-end" >
                                    <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest" > Market Session </span>
                                        < span className = "text-emerald-400 font-mono font-black" > { marketState.market_session.toUpperCase() } </span>
                                            </div>
                                            < div className = "flex flex-col items-end border-l border-slate-800 pl-8 font-mono" >
                                                <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest" > Tactical View </span>
                                                    < span className = "text-blue-400 font-black" > 15M CANDLESTICK </span>
                                                        </div>
                                                        </div>
                                                        </header>

                                                        < div className = "grid grid-cols-1 lg:grid-cols-4 gap-6" >

                                                            {/* Left Column: Intelligence Data */ }
                                                            < div className = "space-y-6 lg:col-span-1" >
                                                                <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-sm" >
                                                                    <h2 className="text-[10px] font-black text-slate-500 mb-6 flex items-center gap-2 tracking-[0.2em] uppercase" >
                                                                        <Activity className="w-4 h-4 text-blue-500" /> Tactical Sensors
                                                                            </h2>
                                                                            < div className = "space-y-4 font-mono" >
                                                                                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 hover:border-emerald-500/30 transition-all group" >
                                                                                    <p className="text-[10px] text-slate-500 mb-1 font-bold uppercase tracking-tighter group-hover:text-emerald-400 transition-colors" > ADX STRENGTH </p>
                                                                                        < div className = "flex items-end gap-2" >
                                                                                            <span className="text-2xl font-black" > { marketState.adx_strength } </span>
                                                                                                < span className = "text-[10px] text-emerald-500 font-bold mb-1 uppercase tracking-tighter" > Stationary </span>
                                                                                                    </div>
                                                                                                    < div className = "w-full bg-slate-800 h-1.5 mt-3 rounded-full overflow-hidden shadow-inner" >
                                                                                                        <div className="bg-emerald-500 h-full shadow-[0_0_12px_rgba(16,185,129,0.8)]" style = {{ width: `${marketState.adx_strength * 2}%` }
}> </div>
    </div>
    </div>
    < div className = "bg-slate-950 p-4 rounded-xl border border-slate-800 hover:border-white/20 transition-all group" >
        <p className="text-[10px] text-slate-500 mb-1 font-bold uppercase tracking-tighter group-hover:text-blue-400" > XAU / USD SPOT </p>
            < div className = "flex items-end gap-2 text-white" >
                <span className="text-2xl font-black tracking-tighter" > ${ marketState.price_close.toFixed(2) } </span>
                    </div>
                    </div>
                    </div>
                    </section>

                    < section className = "bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-sm" >
                        <h2 className="text-[10px] font-black text-slate-500 mb-6 flex items-center gap-2 tracking-[0.2em] uppercase text-red-400" >
                            <Target className="w-4 h-4" /> SMC Structural Intel
                                </h2>
                                < div className = "space-y-3 font-mono" >
                                    <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border-l-4 border-emerald-500 shadow-inner" >
                                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter" > Bias </span>
                                            < span className = "text-xs font-black text-emerald-400 uppercase" > M15 Bullish </span>
                                                </div>
                                                < div className = "flex justify-between items-center p-3 bg-slate-950 rounded-xl border-l-4 border-blue-500 shadow-inner" >
                                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter" > Point of Interest </span>
                                                        < span className = "text-xs font-black text-blue-400 uppercase" > Order Block </span>
                                                            </div>
                                                            </div>
                                                            </section>
                                                            </div>

{/* Center: Live Battlefield Chart */ }
<div className="lg:col-span-3 space-y-6" >
    <section className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl flex flex-col h-[480px]" >
        <div className="p-4 bg-slate-900/80 border-b border-slate-800 flex justify-between items-center px-8" >
            <div className="flex items-center gap-3" >
                <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg" >
                    <TrendingUp className="w-5 h-5" />
                        </div>
                        < h2 className = "text-lg font-black text-white tracking-tight uppercase" >
                            Battlefield Commander < span className = "text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded ml-2 uppercase tracking-widest" > LIVE M15 </span>
                                </h2>
                                </div>
                                < div className = "flex gap-6 font-mono" >
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest" >
                                        <div className="w-3 h-3 rounded-sm bg-[#10b981]" > </div> Bullish
                                            </div>
                                            < div className = "flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest" >
                                                <div className="w-3 h-3 rounded-sm bg-[#f24968]" > </div> Bearish
                                                    </div>
                                                    </div>
                                                    </div>

{/* The Real Chart Engine Container */ }
<div className="flex-grow w-full bg-slate-950 relative" ref = { chartContainerRef } >
    {!libLoaded && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-950/80 z-10" >
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500" > Initializing Chart Engine...</span>
                    </div>
               )}
</div>
    </section>

{/* AI Tactical Control Center */ }
<div className="bg-blue-600/5 border border-blue-500/20 rounded-3xl p-8 relative overflow-hidden shadow-2xl backdrop-blur-md" >
    <div className="absolute top-0 right-0 p-8 opacity-5" > <Crosshair className="w-48 h-48" /> </div>

        < div className = "flex flex-col md:flex-row items-start md:items-center gap-6 mb-8 border-b border-blue-500/10 pb-6" >
            <div className="p-4 bg-blue-500 rounded-2xl text-white shadow-lg shadow-blue-500/20" > <Zap className="w-8 h-8" /> </div>
                < div >
                <h2 className="text-2xl font-black text-white italic tracking-tight uppercase" > AI Battlefield Assessment </h2>
                    < p className = "text-slate-500 text-[10px] tracking-[0.3em] uppercase font-bold font-mono" > General Counsel Intelligence Protocol </p>
                        </div>
                        < div className = "md:ml-auto flex gap-3" >
                            <button onClick={ analyzeBattlefield } className = "px-4 py-2 bg-slate-900 border border-blue-500/30 text-blue-400 rounded-xl text-xs font-bold flex items-center gap-2 hover:bg-blue-500/10 transition-all shadow-lg active:scale-95" >
                                { isAnalyzing?<Loader2 className = "w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />} AI INSIGHT
                                    </button>
                                    < button onClick = { playVoiceBriefing } disabled = { isSpeaking } className = "px-4 py-2 bg-slate-900 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-bold flex items-center gap-2 hover:bg-emerald-500/10 transition-all disabled:opacity-50 active:scale-95" >
                                        { isSpeaking?<Loader2 className = "w-4 h-4 animate-spin" /> : <Volume2 className="w-4 h-4" />} BRIEFING
                                            </button>
                                            </div>
                                            </div>

                                            < div className = "grid md:grid-cols-2 gap-10 mb-8" >
                                                <div className="space-y-6" >
                                                    <div className="group" >
                                                        <label className="text-[10px] text-slate-500 uppercase tracking-widest font-black group-hover:text-blue-400 transition-colors" > Strategic Objective </label>
                                                            < p className = "text-3xl font-black text-white italic tracking-tighter mt-1" > { aiProposal.action } </p>
                                                                </div>
                                                                < div className = "flex gap-12 font-mono" >
                                                                    <div>
                                                                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-black" > Target Zone </label>
                                                                        < p className = "text-xl font-black text-blue-400 tracking-tighter" > ${ aiProposal.range_low } - ${ aiProposal.range_high } </p>
                                                                            </div>
                                                                            < div >
                                                                            <label className="text-[10px] text-slate-500 uppercase tracking-widest font-black" > Risk Level </label>
                                                                                < p className = "text-xl font-black text-orange-500 uppercase tracking-widest" > { aiProposal.risk_level.toUpperCase() } </p>
                                                                                    </div>
                                                                                    </div>
                                                                                    </div>
                                                                                    < div className = "space-y-4" >
                                                                                        <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800/50 italic text-slate-300 text-sm leading-relaxed relative min-h-[100px] shadow-inner" >
                                                                                            <div className="absolute -top-3 -left-2 p-1.5 bg-blue-500 rounded-lg shadow-lg" > <MessageSquare className="w-3 h-3 text-white fill-current" /> </div>
{ aiInsight || aiProposal.rationale }
</div>
    < button onClick = { visualizeBattlefield } className = "w-full py-2 bg-slate-900 border border-slate-800 rounded-xl text-[10px] font-black text-slate-500 hover:text-blue-400 hover:border-blue-500/30 transition-all uppercase tracking-widest flex items-center justify-center gap-2 active:scale-98" >
        { isGeneratingImg?<Loader2 className = "w-3 h-3 animate-spin" /> : <ImageIcon className="w-3 h-3" />} Visual HUD Render
            </button>
            </div>
            </div>

{/* Generated Image Overlay */ }
{
    generatedImage && (
        <div className="mb-8 rounded-3xl overflow-hidden border border-blue-500/20 shadow-2xl relative group h-56 bg-slate-900 shadow-[0_0_30px_rgba(59,130,246,0.1)]" >
            <img src={ generatedImage } alt = "Battlefield View" className = "w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent" > </div>
                    < div className = "absolute bottom-6 left-8 text-[10px] font-black text-blue-400 uppercase tracking-widest flex items-center gap-2 drop-shadow-lg" > <MapIcon className="w-3 h-3" /> Area Recon: M15 Killing Zone Scan </div>
                        < button onClick = {() => setGeneratedImage(null)
} className = "absolute top-6 right-6 p-2 bg-black/60 rounded-full hover:bg-red-500 transition-colors shadow-lg backdrop-blur-md" > <XCircle className="w-5 h-5" /> </button>
    </div>
            )}

{/* Decision System */ }
<div className="space-y-6" >
    <div className="relative group" >
        <textarea 
                  value={ commanderNote }
onChange = {(e) => setCommanderNote(e.target.value)}
placeholder = "Record tactical analysis for LSTM model training..."
className = "w-full bg-slate-950 border border-slate-800 rounded-2xl p-6 text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all min-h-[120px] shadow-inner font-mono"
    />
    <div className="absolute bottom-4 right-4 opacity-10 group-hover:opacity-30 transition-opacity pointer-events-none" > <Mic2 className="w-6 h-6 text-blue-400" /> </div>
        </div>
        < div className = "grid grid-cols-1 md:grid-cols-3 gap-4 font-mono" >
            <button onClick={ () => handleDecision("REJECT") } disabled = { isProcessing } className = "flex items-center justify-center gap-2 py-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 hover:bg-red-500/10 hover:border-red-500/50 hover:text-red-400 transition-all font-black text-xs uppercase tracking-widest active:scale-95" > <XCircle className="w-5 h-5" /> Abort mission </button>
                < button onClick = {() => handleDecision("MODIFY")} disabled = { isProcessing } className = "flex items-center justify-center gap-2 py-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 hover:bg-blue-500/10 hover:border-blue-500/50 hover:text-blue-400 transition-all font-black text-xs uppercase tracking-widest active:scale-95" > <Activity className="w-5 h-5" /> Adjust target </button>
                    < button onClick = {() => handleDecision("APPROVE")} disabled = { isProcessing } className = {`flex items-center justify-center gap-2 py-5 rounded-2xl font-black text-xs transition-all uppercase tracking-widest shadow-xl active:scale-95 ${isProcessing ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600 shadow-blue-500/30'}`}>
                        { isProcessing?<span className = "flex items-center gap-3 animate-pulse">< Zap className = "w-5 h-5 animate-bounce" /> Processing...</span> : <><CheckCircle className="w-5 h-5" / > Approve & Engage </>}
</button>
    </div>
    </div>
    </div>

{/* Historical Logs */ }
<section className="bg-slate-900/30 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl backdrop-blur-sm" >
    <div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center px-8" >
        <h2 className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase flex items-center gap-2" > <History className="w-4 h-4 text-blue-500" /> Engagement History </h2>
            < span className = "text-[10px] text-slate-600 font-bold uppercase tracking-widest font-mono" > LSTM_DATASET_READY </span>
                </div>
                < div className = "max-h-[350px] overflow-y-auto divide-y divide-slate-800/50" >
                {
                    logs.length === 0 ? <div className="p-16 text-center text-slate-700 italic text-sm tracking-widest uppercase font-black opacity-30 font-mono"> Waiting for deployment sequence...</div> : logs.map((log, i) => (
                        < div key={ i } className="p-6 hover:bg-slate-800/20 transition-all px-8 group font-mono" >
                        <div className="flex justify-between items-start mb-3">
                            <div className="flex gap-4 items-center">
                                <span className="text-blue-500 text-xs font-bold bg-blue-500/10 px-2 py-1 rounded">#{ log.engagement_id } </span>
                                    < span className = {`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest border ${log.human_decision.action === 'APPROVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}> { log.human_decision.action } </span>
                                        </div>
                                        < span className = "text-[10px] text-slate-600" > { new Date(log.human_decision.timestamp).toLocaleTimeString() } </span>
                                            </div>
                                            < p className = "text-sm text-slate-300 italic mb-4 leading-relaxed group-hover:text-white transition-colors" > { log.human_decision.note || "No notes logged." } </p>
                                                </div>
              ))}
</div>
    </section>
    </div>
    </div>

{/* FOOTER FIX: Corrected Tag Mismatch */ }
<footer className="mt-12 flex justify-between items-center text-[10px] text-slate-700 uppercase tracking-[0.4em] border-t border-slate-900 pt-8 font-mono" >
    <div className="flex gap-8 font-black" >
        <span className="flex items-center gap-2" > <Zap className="w-3 h-3 text-blue-500" /> Latency: 12ms </span>
            < span className = "flex items-center gap-2 text-emerald-600" > <CheckCircle className="w-3 h-3" /> M15 Real - time Engine Linked </span>
                </div>
                < span className = "font-black hover:text-blue-500 transition-colors cursor-default underline decoration-blue-500/50 underline-offset-4" > Olympus MTF - Gold Conquest OS v1.6.4 </span>
                    </footer>
                    </div>
  );
};

export default App;