'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Flag } from '@/components/ui/flag';
import Link from 'next/link';
import { getCountryCode, formatScore } from '../utils';
import { API_BASE_URL } from '@/lib/api';

interface Participant {
  id: string;
  name: string;
  country?: string;
  rating?: number;
  rating_change?: number;
  rank?: number;
}

export const MatchParticipant = ({ p, id, isSingles }: { p: Participant, id: string, isSingles?: boolean }) => {
  const isCurrentPlayer = p.id === id;
  const pCountryCode = p.country ? getCountryCode(p.country) : null;
  return (
    <span className="inline-flex items-center gap-1.5">
      {pCountryCode && (
        <span className="grayscale-[0.1] brightness-[0.9] rounded-sm opacity-90 w-4.5 h-3 overflow-hidden flex items-center justify-center bg-zinc-800">
          <Flag code={pCountryCode} className="w-full h-full object-cover" />
        </span>
      )}
      <Link 
        href={`/player/${p.id}`}
        className={
          isCurrentPlayer 
            ? `font-black text-sky-400 ${isSingles ? "text-sm" : "text-xs"}` 
            : `hover:text-sky-300 transition-colors ${isSingles ? "text-sm font-black text-zinc-200" : "text-xs font-bold text-zinc-400"}`
        }
        onClick={(e) => e.stopPropagation()}
      >
        {p.name}
      </Link>
    </span>
  );
};

interface MatchFlipCardProps {
  match: {
    match_id: string;
    date: string;
    event: string;
    model: string;
    winner_side: number;
    side1: Participant[];
    side2: Participant[];
    score?: string;
    tournament?: string;
    duration?: number;
    side1_rating?: number;
    side2_rating?: number;
    predicted_prob?: number;
    actual?: number;
    predicted_win_rate?: number;
    round?: string;
  };
  won: boolean;
  isSide1: boolean;
  id: string;
  model: string;
}

export const MatchFlipCard = ({ match, won, isSide1, id, model }: MatchFlipCardProps) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const [lastFlipTime, setLastFlipTime] = useState(0);
  const [showShap, setShowShap] = useState(false);
  const [shapData, setShapData] = useState<Record<string, number> | null>(null);
  const [loadingShap, setLoadingShap] = useState(false);
  const [errorShap, setErrorShap] = useState<string | null>(null);
  
  const ANIMATION_DURATION = 0.5; 
  const COOLDOWN = ANIMATION_DURATION * 2 * 1000; 

  useEffect(() => {
    if (!isFlipped) {
      setShowShap(false);
    }
  }, [isFlipped]);

  const fetchShapData = async () => {
    if (shapData || loadingShap) return;
    setLoadingShap(true);
    setErrorShap(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/predictions/match/${match.match_id}/shap`);
      if (!res.ok) {
        if (res.status === 404) {
          setErrorShap("SHAP Not Found");
        } else {
          setErrorShap("Error loading SHAP");
        }
        return;
      }
      const data = await res.json();
      if (data && data.shap_contributions) {
        setShapData(data.shap_contributions);
      } else {
        setErrorShap("No data available");
      }
    } catch (err) {
      console.error("Error fetching SHAP:", err);
      setErrorShap("Fetch failed");
    } finally {
      setLoadingShap(false);
    }
  };

  const toggleShapMode = () => {
    const nextMode = !showShap;
    setShowShap(nextMode);
    if (nextMode) {
      fetchShapData();
    }
  };
  
  const handleFlip = () => {
    const now = Date.now();
    if (now - lastFlipTime < COOLDOWN) return;
    
    setIsFlipped(!isFlipped);
    setLastFlipTime(now);
  };
  
  const formattedSets = formatScore(match.score || "", isSide1);
  const isSingles = match.event === 'MS' || match.event === 'WS' || match.side1?.length === 1;
  
  return (
    <div 
      className="relative h-[125px] w-full perspective-1000 group"
      onClick={handleFlip}
    >
      <motion.div 
        className="relative w-full h-full transition-all preserve-3d cursor-pointer"
        animate={{ rotateX: isFlipped ? 180 : 0 }}
        transition={{ duration: ANIMATION_DURATION, ease: "easeInOut" }}
      >
        {/* Front Side */}
        <div className="absolute inset-0 backface-hidden bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-4 flex items-center justify-between group-hover:bg-zinc-800/20 transition-colors shadow-lg">
          <div className="grid grid-cols-12 gap-4 items-center w-full">
            <div className="col-span-2 font-mono text-[10px] text-zinc-500">
              <div className="font-bold text-zinc-300 text-xs">{new Date(match.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</div>
              <div className="flex items-center gap-1.5 mt-2 text-sky-400 font-bold text-xs">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span className="tracking-tighter">{match.duration || '--'} min</span>
              </div>
            </div>

            <div className="col-span-3">
              <div className="font-black text-zinc-100 text-base tracking-tight truncate">{match.tournament}</div>
              <div className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest font-mono mt-1">{match.round}</div>
            </div>

            <div className="col-span-1 text-center">
              <span className={`px-2 py-1.5 rounded font-black text-[10px] tracking-tighter ${
                won 
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                  : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
              }`}>
                {won ? "WON" : "LOST"}
              </span>
            </div>

            <div className="col-span-3">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2 truncate">
                  <span className="text-[8px] text-zinc-600 font-mono w-4">S1</span>
                  <div className="flex flex-col gap-0.5 text-zinc-300 text-xs font-bold">
                    {match.side1?.map((p: Participant) => <MatchParticipant key={p.id} p={p} id={id} isSingles={isSingles} />)}
                  </div>
                </div>
                <div className="flex items-center gap-2 truncate">
                  <span className="text-[8px] text-zinc-600 font-mono w-4">S2</span>
                  <div className="flex flex-col gap-0.5 text-zinc-500 text-xs font-semibold">
                    {match.side2?.map((p: Participant) => <MatchParticipant key={p.id} p={p} id={id} isSingles={isSingles} />)}
                  </div>
                </div>
              </div>
            </div>

            <div className="col-span-3 text-right">
              <div className="font-mono text-sky-400 font-black text-lg md:text-xl tracking-tighter">
                <span className="inline-flex items-center gap-1 whitespace-nowrap">
                  {(formattedSets as string[]).map((set, index) => (
                    <React.Fragment key={index}>
                      <span className="whitespace-nowrap">{set}</span>
                      {index < formattedSets.length - 1 && (
                        <span className="text-rose-900 mx-0.5">|</span>
                      )}
                    </React.Fragment>
                  ))}
                </span>
              </div>
            </div>
          </div>
          <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-40 transition-opacity">
            <svg className="w-3 h-3 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          </div>
        </div>

        {/* Back Side (Analytics Redesigned) */}
        <div 
          className="absolute inset-0 backface-hidden bg-zinc-950 border border-sky-500/20 rounded-xl p-4 rotate-x-180 flex items-center shadow-2xl"
        >
          <div className="grid grid-cols-12 gap-2 items-center w-full">
            {(() => {
              const mySide = isSide1 ? (match.side1 || []) : (match.side2 || []);
              const oppSide = isSide1 ? (match.side2 || []) : (match.side1 || []);
              
              const winRate = isSide1 ? match.predicted_win_rate : (1 - (match.predicted_win_rate || 0.5));
              const winRatePct = winRate ? winRate * 100 : 50;
              
              return (
                <>
                  {/* Left Players (Cols 1-4) */}
                  <div className="col-span-4 flex flex-col items-start justify-center pr-2 gap-1.5">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Player</div>
                    {mySide.map((p: Participant) => {
                      const isCurrentPlayer = p.id === id;
                      return (
                        <div key={p.id} className="flex flex-col leading-none w-full">
                          <div className={`text-xs truncate w-full mb-0.5 ${isCurrentPlayer ? 'font-black text-sky-400' : 'font-bold text-zinc-300'}`}>
                            {p.name}
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-black text-sky-400 font-mono">
                              {Math.round((p.rating || 0) + (model === 'whr' ? 1000 : 0))}
                            </span>
                            <span className={`inline-flex items-center px-1.5 py-0.25 rounded text-[9px] font-black font-mono ${
                              (p.rating_change || 0) >= 0 
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {(p.rating_change || 0) >= 0 ? '+' : ''}
                              {(p.rating_change || 0).toFixed(1)}
                            </span>
                            <span className="text-[9px] text-zinc-500 font-bold uppercase font-mono">
                              #{p.rank || '--'}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Center probability tug-of-war / SHAP view (Cols 5-8) */}
                  <div className="col-span-4 flex flex-col items-center justify-center px-2 relative h-full select-none">
                    {/* Header with Title + Toggle Button */}
                    <div className="flex items-center gap-2 mb-2 justify-center w-full">
                      <span className="text-[10px] md:text-[11px] font-black text-zinc-400 uppercase tracking-widest">
                        {showShap ? 'SHAP Factors' : 'Probability'}
                      </span>
                      <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); toggleShapMode(); }}
                        className="p-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800/80 text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer shadow-[0_2px_4px_rgba(0,0,0,0.5)] flex items-center justify-center"
                        title={showShap ? "Show win probability" : "Show SHAP explanations"}
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          {showShap ? (
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          ) : (
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          )}
                        </svg>
                      </button>
                    </div>

                    {!showShap ? (
                      <div className="w-full flex flex-col items-center justify-center px-1">
                        <div className="w-full h-3.5 bg-zinc-800 rounded-full overflow-hidden relative border border-zinc-700/30">
                          <div 
                            className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full transition-all duration-500" 
                            style={{ width: `${winRatePct}%` }}
                          />
                        </div>
                        
                        <div className="mt-2 px-3 py-1 bg-zinc-900 border border-zinc-800 rounded-full text-[10px] md:text-[11px] font-mono font-black text-zinc-300 tracking-wider">
                          {winRate ? `${winRatePct.toFixed(0)}% VS ${(100 - winRatePct).toFixed(0)}%` : 'VS'}
                        </div>
                      </div>
                    ) : (
                      <div className="w-full flex items-center justify-center px-1">
                        {loadingShap ? (
                          <div className="flex items-center gap-1.5 py-2">
                            <span className="w-3.5 h-3.5 border-2 border-sky-400/20 border-t-sky-400 rounded-full animate-spin" />
                            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest animate-pulse">Loading...</span>
                          </div>
                        ) : errorShap ? (
                          <span className="text-[10px] text-zinc-500 font-mono text-center uppercase tracking-wide py-2">{errorShap}</span>
                        ) : shapData ? (
                          <div className="w-full flex flex-col gap-1 text-[10px] md:text-[11px] font-mono leading-none">
                            {Object.entries(shapData)
                              .filter(([key]) => match.event === 'MD' || match.event === 'WD' || match.event === 'XD' || key !== 'Doubles Chemistry')
                              .slice(0, 4) // Show top 4 factors
                              .map(([key, val]) => {
                                const isPlayerAdv = isSide1 ? (val >= 0) : (val <= 0);
                                const displayVal = `${Math.abs(val * 100).toFixed(1)}%`;
                                
                                // Simplify names to fit card
                                let label = key;
                                if (key === "Baseline Skill Gap") label = "Skill";
                                else if (key === "Doubles Chemistry") label = "Synergy";
                                else if (key === "Fatigue & Rest Gap") label = "Rest";
                                else if (key === "H2H Record") label = "H2H";
                                else if (key === "Match Context") label = "Conditions";

                                return (
                                  <div key={key} className="grid grid-cols-12 items-center w-full py-0.5 border-b border-zinc-900/20 last:border-b-0">
                                    {/* Left Value (Player Advantage) */}
                                    <div className="col-span-3 text-left font-black text-emerald-400 text-[9px] md:text-[10px]">
                                      {isPlayerAdv ? `+${displayVal}` : <span className="text-zinc-700/60 font-normal">-</span>}
                                    </div>
                                    
                                    {/* Center Label */}
                                    <div className="col-span-6 text-center text-zinc-400 uppercase text-[8px] md:text-[9px] tracking-tight truncate px-1">
                                      {label}
                                    </div>
                                    
                                    {/* Right Value (Opponent Advantage) */}
                                    <div className="col-span-3 text-right font-black text-emerald-400 text-[9px] md:text-[10px]">
                                      {!isPlayerAdv ? `+${displayVal}` : <span className="text-zinc-700/60 font-normal">-</span>}
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        ) : (
                          <span className="text-[10px] text-zinc-500 font-mono text-center uppercase tracking-wide py-2">No details</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Right Players (Cols 9-11) */}
                  <div className="col-span-3 flex flex-col items-end justify-center pl-2 gap-1.5">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Opponent</div>
                    {oppSide.map((p: Participant) => {
                      return (
                        <div key={p.id} className="flex flex-col items-end leading-none w-full">
                          <div className="text-xs font-bold text-zinc-300 truncate w-full text-right mb-0.5">
                            {p.name}
                          </div>
                          <div className="flex items-center gap-1.5 justify-end">
                            <span className="text-[9px] text-zinc-500 font-bold uppercase font-mono">
                              #{p.rank || '--'}
                            </span>
                            <span className={`inline-flex items-center px-1.5 py-0.25 rounded text-[9px] font-black font-mono ${
                              (p.rating_change || 0) >= 0 
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {(p.rating_change || 0) >= 0 ? '+' : ''}
                              {(p.rating_change || 0).toFixed(1)}
                            </span>
                            <span className="text-sm font-black text-sky-400 font-mono">
                              {Math.round((p.rating || 0) + (model === 'whr' ? 1000 : 0))}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Action Button (Col 12) */}
                  <div className="col-span-1 flex items-center justify-end">
                    <Link 
                      href={`/match/${match.match_id}`} 
                      className="flex items-center justify-center w-8 h-8 bg-zinc-900 hover:bg-zinc-800 rounded-lg border border-zinc-800 transition-all group/btn shadow-lg"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <svg className="w-3.5 h-3.5 text-zinc-400 group-hover/btn:text-white transition-colors" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </Link>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      </motion.div>
    </div>
  );
};
