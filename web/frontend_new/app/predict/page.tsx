'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RetroGrid } from '@/components/magicui/retro-grid';
import { PlayerSelect, SelectablePlayer } from '@/components/player-select';
import { NumberTicker } from '@/components/magicui/number-ticker';
import Flag from 'react-flagpack';
import 'react-flagpack/dist/style.css';
import countryCodes from '@/lib/countryCodes.json';
import { BorderBeam } from '@/components/magicui/border-beam';
import { AnimatedBeam } from '@/components/magicui/animated-beam';
import { API_BASE_URL } from '@/lib/api';

const getCountryCode = (countryName: string) => {
  return (countryCodes as Record<string, string>)[countryName] || countryName || null;
};

interface ContenderSide {
  p1: SelectablePlayer | null;
  p2: SelectablePlayer | null;
  year: number;
}

const SelectionPanel = ({ 
  side, 
  setSide, 
  label,
  isDoubles,
  currentYear
}: { 
  side: ContenderSide; 
  setSide: React.Dispatch<React.SetStateAction<ContenderSide>>; 
  label: string; 
  isDoubles: boolean;
  currentYear: number;
}) => (
  <div className="flex flex-col gap-6 p-8 bg-zinc-900/40 backdrop-blur-xl border border-zinc-800/50 rounded-3xl relative overflow-hidden group">
    <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
    <div className="text-[10px] font-black text-cyan-500 uppercase tracking-[0.3em] mb-2">{label}</div>
    
    <div className="flex flex-col gap-4 relative z-10">
      <PlayerSelect 
        label="Primary Player" 
        placeholder="Search..." 
        onSelect={(p) => setSide({ ...side, p1: p })} 
      />
      
      {isDoubles && (
        <>
          {side.p1 && side.p2 && (
            <div className="h-4 flex justify-center opacity-30">
              <AnimatedBeam duration={2} opacity={0.4} className="rotate-90" />
            </div>
          )}
          <PlayerSelect 
            label="Partner" 
            placeholder="Search..." 
            onSelect={(p) => setSide({ ...side, p2: p })} 
          />
        </>
      )}
    </div>

    <div className="mt-8 relative z-10">
      <div className="flex justify-between items-center mb-4">
        <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Active Era</span>
        <span className="text-xl font-black text-white font-mono">{side.year}</span>
      </div>
      <input 
        type="range" min="2008" max={currentYear} step="1"
        value={side.year}
        onChange={(e) => setSide({ ...side, year: parseInt(e.target.value) })}
        className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
      />
    </div>

    <div className="flex gap-2 relative z-10">
      {side.p1 && (
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 p-3 bg-zinc-950/50 rounded-2xl border border-zinc-800/30 flex items-center gap-3">
           <div className="scale-100 flex-shrink-0">
              <Flag code={getCountryCode(side.p1.country)?.toUpperCase() || 'UN'} size="S" />
           </div>
           <div className="text-[9px] font-black text-zinc-200 uppercase truncate">{side.p1.name}</div>
        </motion.div>
      )}
      {isDoubles && side.p2 && (
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 p-3 bg-zinc-950/50 rounded-2xl border border-zinc-800/30 flex items-center gap-3">
           <div className="scale-100 flex-shrink-0">
              <Flag code={getCountryCode(side.p2.country)?.toUpperCase() || 'UN'} size="S" />
           </div>
           <div className="text-[9px] font-black text-zinc-200 uppercase truncate">{side.p2.name}</div>
        </motion.div>
      )}
    </div>
  </div>
);
SelectionPanel.displayName = 'SelectionPanel';

interface SidePrediction {
  win_prob: number;
  total_strength: number;
  synergy: number;
}

interface PredictionResult {
  side1: SidePrediction;
  side2: SidePrediction;
  model: string;
  meta: {
    date1: string;
    date2: string;
    run_id: string;
  };
}

export default function PredictPage() {
  const [event, setEvent] = useState('MS');
  const [model, setModel] = useState('whr');
  const [side1, setSide1] = useState<ContenderSide>({ p1: null, p2: null, year: 2024 });
  const [side2, setSide2] = useState<ContenderSide>({ p1: null, p2: null, year: 2024 });
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const isDoubles = ['MD', 'WD', 'XD'].includes(event);
  const currentYear = new Date().getFullYear();

  const handlePredict = async () => {
    if (!side1.p1 || !side2.p1) return;
    
    setLoading(true);
    const params = new URLSearchParams({
      side1_p1: side1.p1.player_id,
      side2_p1: side2.p1.player_id,
      date1: `${side1.year}-12-31`,
      date2: `${side2.year}-12-31`,
      event: event,
      model: model,
    });
    
    if (side1.p2) params.append('side1_p2', side1.p2.player_id);
    if (side2.p2) params.append('side2_p2', side2.p2.player_id);

    try {
      const res = await fetch(`${API_BASE_URL}/api/predict/matchup?${params.toString()}`);
      const data = await res.json();
      setPrediction(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getBeamSettings = (synergy: number) => {
    const duration = Math.max(0.4, 2.5 - (synergy / 150));
    const opacity = Math.min(1, 0.3 + (synergy / 300));
    return { duration, opacity };
  };



  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100 overflow-x-hidden p-6 md:p-12">
      <div className="fixed inset-0 pointer-events-none opacity-20">
        <RetroGrid />
      </div>

      <div className="max-w-7xl mx-auto relative z-10">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16">
          <div>
            <h1 className="text-5xl md:text-7xl font-black italic tracking-tighter uppercase leading-none drop-shadow-2xl">
              ERA <span className="text-cyan-500">BATTLE</span>
            </h1>
            <p className="text-zinc-500 text-xs font-mono uppercase tracking-[0.4em] mt-4 ml-1">Analytical Cross-Time Prediction Engine v1.2</p>
          </div>

          <div className="flex flex-col md:flex-row gap-4">
            {/* Model Selector */}
            <div className="flex bg-zinc-950/80 p-1.5 rounded-2xl border border-zinc-900/50 backdrop-blur-md">
              {['elo', 'whr', 'bwf'].map(m => (
                <button
                  key={m}
                  onClick={() => {
                    setModel(m);
                    setPrediction(null);
                  }}
                  className={`px-4 py-2 text-xs font-black rounded-xl transition-all uppercase ${
                    model === m ? 'bg-zinc-100 text-black shadow-md' : 'text-zinc-500 hover:text-white'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>

            {/* Event Selector */}
            <div className="flex bg-zinc-900/80 p-1.5 rounded-2xl border border-zinc-800/50 backdrop-blur-md">
              {['MS', 'WS', 'MD', 'WD', 'XD'].map(ev => (
                <button
                  key={ev}
                  onClick={() => {
                    setEvent(ev);
                    setPrediction(null);
                  }}
                  className={`px-6 py-2.5 text-xs font-black rounded-xl transition-all ${
                    event === ev ? 'bg-cyan-500 text-black shadow-lg shadow-cyan-500/20' : 'text-zinc-500 hover:text-white'
                  }`}
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-7 gap-8 items-center">
          <div className="lg:col-span-3">
             <SelectionPanel side={side1} setSide={setSide1} label="CONTENDER ALPHA" isDoubles={isDoubles} currentYear={currentYear} />
          </div>

          <div className="lg:col-span-1 flex flex-col items-center gap-8 py-8">
             <div className="w-16 h-16 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-xl font-black italic text-zinc-600">VS</div>
             <button 
               onClick={handlePredict}
               disabled={!side1.p1 || !side2.p1 || loading}
               className="group relative px-8 py-4 bg-white text-black font-black uppercase text-xs tracking-[0.2em] rounded-2xl disabled:opacity-20 disabled:cursor-not-allowed hover:bg-cyan-400 hover:scale-105 transition-all shadow-[0_0_40px_rgba(255,255,255,0.1)]"
             >
                {loading ? 'CALCULATING...' : 'RUN PREDICTION'}
                <BorderBeam className="opacity-0 group-hover:opacity-100 transition-opacity" size={100} duration={4} />
             </button>
          </div>

          <div className="lg:col-span-3">
             <SelectionPanel side={side2} setSide={setSide2} label="CONTENDER OMEGA" isDoubles={isDoubles} currentYear={currentYear} />
          </div>
        </div>

        {/* Results Area */}
        <AnimatePresence>
          {prediction && (
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 40 }}
              className="mt-16 p-12 bg-zinc-900/60 rounded-[40px] border border-cyan-500/20 relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,0.1),transparent)]" />
              <BorderBeam duration={10} size={500} colorFrom="#22d3ee" colorTo="#3b82f6" />
              
              <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-12 items-center">
                <div className="text-center md:text-left">
                  <div className="text-zinc-500 text-[10px] font-black uppercase tracking-widest mb-2">Alpha Probability</div>
                  <div className="text-7xl font-black text-white font-mono leading-none">
                    <NumberTicker value={prediction.side1.win_prob} />%
                  </div>
                  <div className="mt-4 text-[10px] text-zinc-600 font-bold uppercase tracking-[0.2em]">{model === 'bwf' ? 'Points' : 'Rating'}: {Math.round(prediction.side1.total_strength + (model === 'bwf' ? 0 : isDoubles ? 2000 : 1000))}</div>
                  
                  {isDoubles && (
                    <div className="mt-4 flex items-center gap-3">
                       <div className="w-16">
                          <AnimatedBeam {...getBeamSettings(prediction.side1.synergy)} />
                       </div>
                       <span className="text-[9px] font-black text-cyan-500 uppercase tracking-widest">Synergy: {prediction.side1.synergy}</span>
                    </div>
                  )}
                </div>

                <div className="flex flex-col items-center gap-4">
                  <div className="w-full h-4 bg-zinc-950 rounded-full overflow-hidden border border-zinc-800 p-0.5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${prediction.side1.win_prob}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full shadow-[0_0_20px_rgba(34,211,238,0.3)]"
                    />
                  </div>
                  <div className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.4em]">Battle Momentum</div>
                </div>

                <div className="text-center md:text-right">
                  <div className="text-zinc-500 text-[10px] font-black uppercase tracking-widest mb-2">Omega Probability</div>
                  <div className="text-7xl font-black text-white font-mono leading-none">
                    <NumberTicker value={prediction.side2.win_prob} />%
                  </div>
                  <div className="mt-4 text-[10px] text-zinc-600 font-bold uppercase tracking-[0.2em]">{model === 'bwf' ? 'Points' : 'Rating'}: {Math.round(prediction.side2.total_strength + (model === 'bwf' ? 0 : isDoubles ? 2000 : 1000))}</div>
                  
                  {isDoubles && (
                    <div className="mt-4 flex items-center justify-end gap-3">
                       <span className="text-[9px] font-black text-cyan-500 uppercase tracking-widest">Synergy: {prediction.side2.synergy}</span>
                       <div className="w-16">
                          <AnimatedBeam {...getBeamSettings(prediction.side2.synergy)} />
                       </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-12 pt-8 border-t border-zinc-800/50 flex flex-col md:flex-row justify-between items-center gap-6">
                 <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Model: {prediction.model || "WHR"}</span>
                 </div>
                 <div className="text-[10px] font-mono text-zinc-600">ERA-DIF: {Math.abs(parseInt(prediction.meta.date1.split('-')[0], 10) - parseInt(prediction.meta.date2.split('-')[0], 10))}Y</div>
                 <div className="flex items-center gap-2 px-4 py-2 bg-zinc-950/80 rounded-xl border border-zinc-800">
                    <span className="text-[9px] font-black text-zinc-500 uppercase">Engine ID:</span>
                    <span className="text-[9px] font-mono text-zinc-300 truncate max-w-[150px]">{prediction.meta.run_id}</span>
                 </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
