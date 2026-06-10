'use client';

import React, { useState, useEffect } from 'react';
import { NumberTicker } from '@/components/magicui/number-ticker';
import { API_BASE_URL } from '@/lib/api';

interface GlobalStats {
  total_matches: number;
  total_players: number;
  first_match: string;
  last_update: string;
}

export function GlobalStatsCard() {
  const [stats, setStats] = useState<GlobalStats | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/dashboard/summary`)
      .then(res => res.json())
      .then(setStats)
      .catch(console.error);
  }, []);

  if (!stats) return <div className="h-[232px] flex items-center justify-center text-[10px] text-zinc-700 animate-pulse uppercase tracking-widest font-black">Connecting to Core...</div>;

  return (
    <div className="h-[232px] flex flex-col relative overflow-hidden group">
      
      <h3 className="text-zinc-500 text-[10px] font-mono uppercase tracking-[0.2em] mb-6 relative z-10">Database Pulse</h3>
      
      <div className="flex-grow flex items-center justify-between gap-3 relative z-10">
        <div className="space-y-10 flex-grow">
          <div>
            <div className="text-5xl font-black text-white tracking-tighter leading-none drop-shadow-[0_0_15px_rgba(255,255,255,0.15)] group-hover:text-cyan-400 group-hover:drop-shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all duration-500">
              <NumberTicker value={stats.total_matches} />
            </div>
            <div className="text-[10px] text-zinc-500 uppercase font-black tracking-[0.2em] opacity-60 mt-2">Matches Analyzed</div>
          </div>
          <div>
            <div className="text-5xl font-black text-white tracking-tighter leading-none drop-shadow-[0_0_15px_rgba(255,255,255,0.15)] group-hover:text-cyan-400 group-hover:drop-shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all duration-500">
              <NumberTicker value={stats.total_players} />
            </div>
            <div className="text-[10px] text-zinc-500 uppercase font-black tracking-[0.2em] opacity-60 mt-2">Total Players Ranked</div>
          </div>
        </div>

        <div className="h-32 border-l border-zinc-800/50 pl-4 pr-0 flex flex-col justify-center flex-shrink-0">
          <div className="text-zinc-600 text-[8px] font-black uppercase mb-3 tracking-widest leading-none">Temporal Scope</div>
          <div className="text-xl font-black text-white font-mono leading-none mb-1 uppercase tracking-tighter">
            {new Date(stats.first_match).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
          </div>
          <div className="text-zinc-800 text-[9px] font-black uppercase my-2 tracking-[0.3em]">TO</div>
          <div className="text-xl font-black text-cyan-500 font-mono leading-none uppercase tracking-tighter drop-shadow-[0_0_10px_rgba(6,182,212,0.3)]">
            {new Date(stats.last_update).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-3 text-[9px] text-zinc-500 font-mono font-black uppercase tracking-[0.3em] relative z-10">
        <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_#06b6d4] animate-pulse" />
        <span className="animate-pulse">Live Analytics active</span>
      </div>
    </div>
  );
}
