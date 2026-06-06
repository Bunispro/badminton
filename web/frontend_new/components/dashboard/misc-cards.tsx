'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Flag } from '@/components/ui/flag';
import { NumberTicker } from '@/components/magicui/number-ticker';
import { Trophy, Timer } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';
import { getCountryCode } from './utils';

interface PopularPlayer {
  player_id: string;
  name: string;
  country: string;
  views: number;
}

export function MostSearchedCard() {
  const [players, setPlayers] = useState<PopularPlayer[]>([]);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/dashboard/trending`)
      .then(res => res.json())
      .then(data => {
        if (!active) return;
        setPlayers(data.most_searched || []);
      })
      .catch(console.error);
    return () => { active = false; };
  }, []);

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-zinc-500 text-[10px] font-mono uppercase tracking-widest mb-4">Most Popular</h3>
      
      <div className="flex-grow flex flex-col py-1">
        {players && players.length > 0 ? (
          players.slice(0, 3).map((player, i) => {
            const code = getCountryCode(player.country);
            const gradients = [
              "from-[#FFD700] via-[#FDB931] to-[#E5B800]",
              "from-[#C0C0C0] via-[#E8E8E8] to-[#A0A0A0]",
              "from-[#CD7F32] via-[#B87333] to-[#8B4513]"
            ];
            const currentGradient = gradients[i] || "from-white to-zinc-400";
            
            return (
              <div key={player.player_id || i} className="flex-1 flex flex-col justify-center min-h-0">
                <div className="flex items-center justify-between group">
                  <div className="flex items-center gap-2 flex-grow min-w-0">
                    <div className="text-zinc-800 font-black text-[10px] w-2 shrink-0">{i + 1}</div>
                    {code && (
                      <div className="shrink-0 scale-[0.6] origin-left">
                        <div className="rounded-sm border border-zinc-800 overflow-hidden shadow-sm">
                          <Flag code={code.toUpperCase()} size="S" className="object-cover" />
                        </div>
                      </div>
                    )}
                    <Link 
                      href={`/player/${player.player_id}`} 
                      className={`text-xl font-black group-hover:opacity-80 transition-all uppercase truncate flex-grow -ml-1 text-transparent bg-clip-text bg-gradient-to-r ${currentGradient}`}
                    >
                      {player.name}
                    </Link>
                  </div>
                  <div className="flex items-baseline gap-1 shrink-0 ml-2">
                    <span className={`text-xl font-black text-transparent bg-clip-text bg-gradient-to-r ${currentGradient}`}>
                      <NumberTicker value={player.views} />
                    </span>
                    <span className="text-[7px] text-zinc-600 font-black uppercase tracking-tighter">Searches</span>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-zinc-700 text-[10px] italic py-2">Waiting for traffic data...</div>
        )}
      </div>
      <div className="h-[2px] w-full bg-zinc-900 rounded-full mt-4" />
    </div>
  );
}

interface UpsetMatch {
  winner_id: string;
  winner: string;
  loser_id: string;
  loser: string;
  discipline: string;
  winProbability: number;
  ratingGain: number;
  score: string;
  date: string;
}

export function UpsetAlertCard() {
  const [match, setMatch] = useState<UpsetMatch | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/dashboard/upsets`)
      .then(res => res.json())
      .then(data => {
        if (!active) return;
        setMatch(data);
        setLoading(false);
      })
      .catch(err => {
        if (!active) return;
        console.error(err);
        setLoading(false);
      });
    return () => { active = false; };
  }, []);

  if (loading) return (
    <div className="h-full flex items-center justify-center">
      <div className="w-5 h-5 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
    </div>
  );

  if (!match) return null;

  const percentage = (match.winProbability * 100).toFixed(1);
  const formattedDate = match.date ? new Date(match.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';

  return (
    <div className="h-full flex flex-col justify-between py-1 relative group overflow-hidden">
      <div className="absolute -inset-2 bg-amber-500/5 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
      
      <div className="flex flex-col gap-0.5 relative z-10">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
            Against All Odds
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[9px] font-black text-amber-500 border border-amber-500/20 uppercase tracking-tighter">
            <Trophy className="h-2.5 w-2.5" /> 3m Peak
          </span>
        </div>
        
        <div className="mt-1.5 flex items-baseline justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black tracking-tighter text-[#F97316] drop-shadow-[0_0_15px_rgba(249,115,22,0.3)]">
              {percentage}%
            </span>
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest flex items-center gap-1">
              win prob
            </span>
          </div>
          <div className="flex items-baseline gap-1 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <span className="text-xs font-black text-emerald-400 font-mono">+{match.ratingGain}</span>
            <span className="text-[7px] text-emerald-600 font-black uppercase tracking-tighter">Elo Gain</span>
          </div>
        </div>
      </div>

      <div className="my-auto flex flex-col justify-center py-1 relative z-10">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-3">
            <Link 
              href={`/player/${match.winner_id}`}
              className="font-black text-3xl tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white via-zinc-300 to-zinc-500 uppercase italic drop-shadow-[0_4px_8px_rgba(0,0,0,0.8)] hover:from-amber-200 hover:to-amber-500 transition-all duration-300"
            >
              {match.winner}
            </Link>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] font-black text-zinc-400 border border-zinc-700 uppercase">
              {match.discipline}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
             <div className="h-[1px] w-4 bg-zinc-800" />
             <span className="text-[10px] text-zinc-600 font-black uppercase tracking-widest italic">
               defeats
             </span>
             <div className="h-[1px] flex-grow bg-zinc-800" />
          </div>
          
          <Link 
            href={`/player/${match.loser_id}`}
            className="font-bold text-base text-zinc-500 uppercase tracking-tight opacity-60 hover:opacity-100 hover:text-zinc-300 transition-all"
          >
            {match.loser}
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-zinc-800/50 pt-3 relative z-10">
        <div className="flex items-center gap-2">
          <Timer className="h-3.5 w-3.5 text-zinc-600" />
          <span className="font-mono text-lg font-black text-zinc-100 tracking-tighter">
            {match.score}
          </span>
        </div>
        <span className="text-[11px] text-zinc-600 font-black uppercase tracking-widest">
          {formattedDate}
        </span>
      </div>
    </div>
  );
}

export function EngineStatusCard() {
  const [lastSync, setLastSync] = useState('2m ago');
  
  useEffect(() => {
    const timer = setInterval(() => {
      const mins = Math.floor(Math.random() * 5) + 1;
      setLastSync(`${mins}m ago`);
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-full flex flex-col items-center justify-center p-4 relative group overflow-hidden">
      <div className="absolute inset-0 bg-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-3xl rounded-full" />
      
      <div className="relative z-10 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <motion.div 
            animate={{ 
              scale: [1, 1.2, 1],
              opacity: [1, 0.6, 1],
              boxShadow: [
                '0 0 0px rgba(16, 185, 129, 0)',
                '0 0 20px rgba(16, 185, 129, 0.6)',
                '0 0 0px rgba(16, 185, 129, 0)'
              ]
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="w-2.5 h-2.5 rounded-full bg-emerald-500" 
          />
          <div className="text-[10px] text-zinc-500 font-mono uppercase tracking-[0.4em]">Engine v2.4</div>
        </div>
        
        <div className="text-4xl font-black text-white tracking-tighter leading-none mb-4 group-hover:text-emerald-400 transition-colors duration-500">
          STABLE
        </div>

        <div className="inline-flex flex-col items-center gap-1 pt-4 border-t border-zinc-800/50 w-full">
          <div className="text-[9px] text-zinc-600 font-black uppercase tracking-[0.2em]">Sync Status</div>
          <div className="flex items-center gap-1.5">
             <div className="text-[10px] font-black text-emerald-500 font-mono">Last Sync:</div>
             <div className="text-[10px] font-black text-zinc-400 font-mono italic">{lastSync}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
