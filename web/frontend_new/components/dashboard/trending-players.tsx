'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { Flag } from '@/components/ui/flag';
import { NumberTicker } from '@/components/magicui/number-ticker';
import { API_BASE_URL } from '@/lib/api';
import { getCountryCode } from './utils';

interface TrendingPlayer {
  player_id: string;
  name: string;
  country: string;
  gain: number;
  current_rating: number;
  synergy_partner?: {
    player_id: string;
    name: string;
  };
}

export function TrendingPlayersCard() {
  const [movers, setMovers] = useState<TrendingPlayer[]>([]);
  const [activeEvent, setActiveEvent] = useState('MS');
  const [period, setPeriod] = useState<'1m' | '3m'>('3m');
  const [loading, setLoading] = useState(true);
  const events = ['MS', 'WS', 'MD', 'WD', 'XD'];

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/dashboard/trending?event=${activeEvent}&period=${period}`)
      .then(res => res.json())
      .then(data => {
        if (!active) return;
        setMovers(data.top_movers || []);
        setLoading(false);
      })
      .catch(err => {
        if (!active) return;
        console.error(err);
        setLoading(false);
      });
    return () => { active = false; };
  }, [activeEvent, period]);

  const switchEvent = (dir: 'next' | 'prev') => {
    setLoading(true);
    const idx = events.indexOf(activeEvent);
    const nextIdx = dir === 'next' ? (idx + 1) % events.length : (idx - 1 + events.length) % events.length;
    setActiveEvent(events[nextIdx]);
  };

  return (
    <div className="h-[136px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-zinc-500 text-[10px] font-mono uppercase tracking-widest">Global Top Movers</h3>
          <div className="flex items-center bg-zinc-900/80 rounded-md p-0.5 border border-zinc-800/50">
            <button 
              onClick={() => { setLoading(true); setPeriod('1m'); }}
              className={`px-1.5 py-0.5 text-[8px] font-black rounded transition-all ${period === '1m' ? 'bg-emerald-500/20 text-emerald-400' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              1M
            </button>
            <button 
              onClick={() => { setLoading(true); setPeriod('3m'); }}
              className={`px-1.5 py-0.5 text-[8px] font-black rounded transition-all ${period === '3m' ? 'bg-emerald-500/20 text-emerald-400' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              3M
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
           <button onClick={() => switchEvent('prev')} className="p-1 hover:bg-zinc-800/50 rounded-md transition-colors text-zinc-500 hover:text-zinc-300">
             <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
           </button>
           <span className="text-[10px] font-black text-emerald-400 font-mono w-6 text-center">{activeEvent}</span>
           <button onClick={() => switchEvent('next')} className="p-1 hover:bg-zinc-800/50 rounded-md transition-colors text-zinc-500 hover:text-zinc-300">
             <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
           </button>
        </div>
      </div>

      <div className="flex-grow relative">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div 
              key="loading"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center bg-zinc-900/40 backdrop-blur-[1px] z-20 rounded-xl"
            >
              <div className="w-5 h-5 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
            </motion.div>
          ) : movers && movers.length > 0 ? (
            <motion.div 
              key={activeEvent}
              initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}
              className="space-y-4"
            >
              {movers.slice(0, 1).map((player, i) => {
                const code = getCountryCode(player.country);
                return (
                  <div key={player.player_id || i} className="flex items-center justify-between group">
                    <div className="flex items-center gap-3 flex-1 overflow-hidden">
                      <div className="text-zinc-800 font-black text-xs w-3 shrink-0">{i + 1}</div>
                      {code && (
                        <div className="shrink-0 scale-[0.6] origin-left">
                          <div className="rounded-sm border border-zinc-800 overflow-hidden shadow-sm">
                            <Flag code={code.toUpperCase()} size="S" className="object-cover" />
                          </div>
                        </div>
                      )}
                      <div className="flex flex-col flex-grow min-w-0">
                        <Link href={`/player/${player.player_id}`} className="text-xs font-black text-zinc-100 group-hover:text-emerald-400 transition-colors uppercase leading-tight">
                          {player.name}
                        </Link>
                        {player.synergy_partner && (
                          <>
                            <div className="h-[1px] w-full bg-zinc-800/50 my-1" />
                            <Link href={`/player/${player.synergy_partner.player_id}`} className="text-xs font-black text-zinc-100 group-hover:text-emerald-500 transition-colors uppercase leading-tight">
                              {player.synergy_partner.name}
                            </Link>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="text-[#00FF9D] font-mono text-sm font-black drop-shadow-[0_0_8px_rgba(0,255,157,0.4)] shrink-0 ml-2">
                      +<NumberTicker value={player.gain || 0} />
                    </div>
                  </div>
                );
              })}
            </motion.div>
          ) : (
            <motion.div 
              key="empty"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="text-zinc-700 text-[10px] italic py-2"
            >
              Scanning for {activeEvent} breakthroughs...
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
