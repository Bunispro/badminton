'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '@/lib/api';

interface SynergyPartner {
  partner_id: string;
  partner_name: string;
}

interface Player {
  id: string;
  name: string;
  country?: string;
}

interface Prediction {
  prob_side1: number;
  prob_side2: number;
}

interface H2H {
  summary: {
    total: number;
    side1_wins: number;
    side2_wins: number;
  };
}

interface PredictionCardProps {
  playerId: string;
  playerName: string;
  event: string;
  model: string;
  synergyList?: SynergyPartner[];
}

export const PredictionCard = ({ playerId, playerName, event, model, synergyList }: PredictionCardProps) => {
  const [side1, setSide1] = useState<Player[]>([]);
  const [side2, setSide2] = useState<Player[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [h2h, setH2h] = useState<H2H | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Player[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  
  const isDoubles = ['MD', 'WD', 'XD'].includes(event);
  const maxPlayers = isDoubles ? 2 : 1;

  useEffect(() => {
    if (!playerId || !playerName) return;
    const p1 = { id: playerId, name: playerName };
    if (isDoubles && synergyList?.[0]) {
      const timer = setTimeout(() => {
        setSide1([p1, { id: synergyList[0].partner_id, name: synergyList[0].partner_name }]);
      }, 0);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setSide1([p1]);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [playerId, playerName, event, synergyList, isDoubles]);

  const fetchPrediction = useCallback(async () => {
    setTimeout(() => setLoading(true), 0);
    try {
      const s1 = side1.map(p => p.id).join(',');
      const s2 = side2.map(p => p.id).join(',');
      
      const [predRes, h2hRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/predict_match_v2?side1=${s1}&side2=${s2}&event=${event}&model=${model}`),
        fetch(`${API_BASE_URL}/api/headtohead_v2?side1=${s1}&side2=${s2}&event=${event}`)
      ]);
      
      if (predRes.ok) setPrediction(await predRes.json());
      if (h2hRes.ok) setH2h(await h2hRes.json());
    } catch (error) {
      console.error("Prediction failed:", error);
    } finally {
      setLoading(false);
    }
  }, [side1, side2, event, model]);

  useEffect(() => {
    if (side1.length === maxPlayers && side2.length === maxPlayers) {
      const timer = setTimeout(() => {
        fetchPrediction();
      }, 0);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setPrediction(null);
        setH2h(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [side1, side2, maxPlayers, fetchPrediction]);

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (val.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/players/search?q=${encodeURIComponent(val)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.slice(0, 8));
        setShowDropdown(true);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const addPlayer = (p: Player, side: 1 | 2) => {
    if (side === 1) {
      if (side1.some(x => x.id === p.id)) return;
      if (side1.length < maxPlayers) setSide1([...side1, p]);
    } else {
      if (side2.some(x => x.id === p.id)) return;
      if (side2.length < maxPlayers) setSide2([...side2, p]);
    }
    setSearchQuery("");
    setShowDropdown(false);
  };

  const removePlayer = (pid: string, side: 1 | 2) => {
    if (side === 1) {
      if (pid === playerId) return; 
      setSide1(side1.filter(p => p.id !== pid));
    } else {
      setSide2(side2.filter(p => p.id !== pid));
    }
  };

  return (
    <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/><line x1="12" x2="12" y1="7" y2="13"/><line x1="9" x2="15" y1="10" y2="10"/></svg>
      </div>

      <h2 className="text-lg font-bold text-zinc-100 mb-6 flex items-center gap-2">
        Match Prediction
        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20 font-mono uppercase tracking-widest">v2.0 Beta</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-11 gap-6 items-center">
        <div className="md:col-span-4 space-y-3">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Your Team</div>
          <div className="flex flex-col gap-2">
            {side1.map(p => (
              <div key={p.id} className="flex items-center justify-between bg-zinc-800/50 border border-zinc-700/50 p-2 rounded-lg">
                <span className="text-sm font-medium text-zinc-100 truncate">{p.name}</span>
                {p.id !== playerId && (
                  <button onClick={() => removePlayer(p.id, 1)} className="text-zinc-500 hover:text-rose-400 p-1">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                  </button>
                )}
              </div>
            ))}
            {side1.length < maxPlayers && (
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Add Partner..." 
                  className="w-full bg-emerald-500/5 border border-emerald-500/20 p-2 rounded-lg text-xs focus:outline-none focus:border-emerald-500/50"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                />
              </div>
            )}
          </div>
        </div>

        <div className="md:col-span-3 flex flex-col items-center justify-center py-4 relative">
          <div className="text-3xl font-black text-zinc-800 absolute -z-10 tracking-tighter scale-150">VS</div>
          
          {loading ? (
            <div className="animate-pulse text-xs font-mono text-emerald-500 uppercase">Calculating...</div>
          ) : prediction ? (
            <div className="text-center space-y-2">
              <div className="flex items-center gap-4">
                <div className="flex flex-col items-center">
                  <div className="text-2xl font-bold text-emerald-400">{(prediction.prob_side1 * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-zinc-500 uppercase">Win Rate</div>
                </div>
                <div className="h-8 w-px bg-zinc-800"></div>
                <div className="flex flex-col items-center">
                  <div className="text-2xl font-bold text-zinc-400">{(prediction.prob_side2 * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-zinc-500 uppercase">Opponent</div>
                </div>
              </div>
              
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden flex">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${prediction.prob_side1 * 100}%` }}
                  className="h-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                />
                <div className="flex-1 bg-zinc-700" />
              </div>

              {h2h && h2h.summary.total > 0 && (
                <div className="text-[10px] font-mono text-zinc-500 bg-zinc-800/50 px-2 py-1 rounded">
                  H2H: <span className="text-emerald-400">{h2h.summary.side1_wins}</span> - <span className="text-rose-400">{h2h.summary.side2_wins}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-zinc-600 font-mono text-center px-4 italic leading-tight">
              Select opponents to calculate victory probability.
            </div>
          )}
        </div>

        <div className="md:col-span-4 space-y-3">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest text-right">Opponent Team</div>
          <div className="flex flex-col gap-2">
            {side2.map(p => (
              <div key={p.id} className="flex items-center justify-between bg-zinc-800/50 border border-zinc-700/50 p-2 rounded-lg">
                <span className="text-sm font-medium text-zinc-100 truncate">{p.name}</span>
                <button onClick={() => removePlayer(p.id, 2)} className="text-zinc-500 hover:text-rose-400 p-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
              </div>
            ))}
            {side2.length < maxPlayers && (
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Search Opponent..." 
                  className="w-full bg-zinc-800/50 border border-zinc-700/50 p-2 rounded-lg text-xs focus:outline-none focus:border-zinc-500"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                />
                
                <AnimatePresence>
                  {showDropdown && searchResults.length > 0 && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute z-50 left-0 right-0 mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
                    >
                      {searchResults.map(p => (
                        <button
                          key={p.id}
                          onClick={() => addPlayer(p, 2)}
                          className="w-full text-left px-4 py-2 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors border-b border-zinc-800/50 last:border-0"
                        >
                          <div className="font-bold">{p.name}</div>
                          <div className="text-[9px] text-zinc-500 uppercase">{p.country}</div>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
