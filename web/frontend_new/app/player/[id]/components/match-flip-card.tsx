'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Flag } from '@/components/ui/flag';
import Link from 'next/link';
import { getCountryCode, formatScore } from '../utils';

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
  const ANIMATION_DURATION = 0.5; 
  const COOLDOWN = ANIMATION_DURATION * 2 * 1000; 
  
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
                  <div className="flex gap-1 flex-wrap text-zinc-300 text-xs font-bold">
                    {match.side1?.map((p: Participant) => <MatchParticipant key={p.id} p={p} id={id} isSingles={isSingles} />)}
                  </div>
                </div>
                <div className="flex items-center gap-2 truncate">
                  <span className="text-[8px] text-zinc-600 font-mono w-4">S2</span>
                  <div className="flex gap-1 flex-wrap text-zinc-500 text-xs font-semibold">
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
              const me = isSide1 
                ? (match.side1?.find((p: Participant) => p.id === id) || match.side1?.[0])
                : (match.side2?.find((p: Participant) => p.id === id) || match.side2?.[0]);
              const opp = isSide1 
                ? match.side2?.[0] 
                : match.side1?.[0];
              
              const winRate = isSide1 ? match.predicted_win_rate : (1 - (match.predicted_win_rate || 0.5));
              const winRatePct = winRate ? winRate * 100 : 50;
              
              return (
                <>
                  {/* Left Player (Cols 1-4) */}
                  <div className="col-span-4 flex flex-col items-start justify-center pr-2">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Player</div>
                    <div className="text-sm font-black text-zinc-100 truncate w-full mb-1">
                      {me?.name}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-black text-sky-400 font-mono">
                        {Math.round((me?.rating || 0) + (model === 'whr' ? 1000 : 0))}
                      </span>
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-black font-mono ${
                        (me?.rating_change || 0) >= 0 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {(me?.rating_change || 0) >= 0 ? '+' : ''}
                        {(me?.rating_change || 0).toFixed(1)}
                      </span>
                    </div>
                    <div className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider mt-1">
                      Rank: <span className="text-zinc-200">#{me?.rank || '--'}</span>
                    </div>
                  </div>

                  {/* Center probability tug-of-war (Cols 5-8) */}
                  <div className="col-span-4 flex flex-col items-center justify-center px-4 relative">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Probability</div>
                    
                    <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden relative border border-zinc-700/30">
                      <div 
                        className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full transition-all duration-500" 
                        style={{ width: `${winRatePct}%` }}
                      />
                    </div>
                    
                    <div className="mt-2.5 px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded-full text-[9px] font-mono font-black text-zinc-400 tracking-wider">
                      {winRate ? `${winRatePct.toFixed(0)}% VS ${(100 - winRatePct).toFixed(0)}%` : 'VS'}
                    </div>
                  </div>

                  {/* Right Player (Cols 9-11) */}
                  <div className="col-span-3 flex flex-col items-end justify-center pl-2">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-0.5">Opponent</div>
                    <div className="text-sm font-black text-zinc-100 truncate w-full text-right mb-1">
                      {opp?.name}
                    </div>
                    <div className="flex items-center gap-2 justify-end">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-black font-mono ${
                        (opp?.rating_change || 0) >= 0 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {(opp?.rating_change || 0) >= 0 ? '+' : ''}
                        {(opp?.rating_change || 0).toFixed(1)}
                      </span>
                      <span className="text-2xl font-black text-sky-400 font-mono">
                        {Math.round((opp?.rating || 0) + (model === 'whr' ? 1000 : 0))}
                      </span>
                    </div>
                    <div className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider mt-1">
                      Rank: <span className="text-zinc-200">#{opp?.rank || '--'}</span>
                    </div>
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
