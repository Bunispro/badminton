'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { BorderBeam } from "@/components/magicui/border-beam";
import { RetroGrid } from '@/components/magicui/retro-grid';

interface StatsSectionProps {
  stats: {
    current_rating?: number;
    current_rank?: number;
    total_players?: number;
    win_rate?: number;
    wins?: number;
    total_matches?: number;
    dominance_score?: number;
    synergy_list?: {
      partner_id: string;
      partner_name: string;
      synergy: number;
      total_matches: number;
    }[];
    opponents?: {
      opponent_id: string;
      opponent_name: string;
      wins: number;
      total_matches: number;
      win_rate: number;
    }[];
  } | null;
  winStreak: number;
  daysSinceLastMatch: number | null;
  model: string;
  event: string;
}

export const StatsSection = ({ stats, winStreak, daysSinceLastMatch, model, event }: StatsSectionProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Rating */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-6 flex flex-col justify-between col-span-1 border-t-2 border-t-cyan-500">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
            {model === 'elo' ? 'Elo' : model === 'whr' ? 'WHR' : 'BWF'} {model === 'bwf' ? 'Points' : 'Rating'}
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <div className="text-4xl font-bold text-sky-400">
              {stats?.current_rating !== undefined && stats?.current_rating !== null
                ? Math.round(stats.current_rating + (model === 'whr' ? 1000 : 0))
                : 'N/A'}
            </div>
            <div className="text-sm text-zinc-500">{model === 'elo' ? 'Elo' : model === 'whr' ? 'WHR' : 'BWF'}</div>
          </div>
        </div>
        <div className="text-xs text-zinc-600 mt-2">Current skill estimate</div>
      </div>

      {/* Card 2: Rank */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-6 flex flex-col justify-between col-span-1 border-t-2 border-t-emerald-500">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Rank</div>
          <div className="text-4xl font-bold text-emerald-400 mt-2">#{stats?.current_rank || 'N/A'}</div>
        </div>
        {!!stats?.current_rank && !!stats?.total_players && stats?.total_players > 0 && (
          <div className="mt-2">
            <div className="text-sm font-bold text-emerald-600">
              Top {Math.max(0.1, Math.round((stats.current_rank / stats.total_players) * 100))}%
            </div>
            <div className="text-xs text-zinc-600">of {stats.total_players} players</div>
          </div>
        )}
      </div>

      {/* Card 3: Win Rate */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-4 flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Win Rate</div>
          <div className="text-3xl font-bold text-zinc-100 mt-2">{stats?.win_rate}%</div>
        </div>
        <div className="text-xs text-zinc-600 mt-2">{stats?.wins} Wins / {stats?.total_matches} Matches</div>
      </div>

      {/* Card 4: Win Streak */}
      <motion.div 
        className={`bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-4 flex flex-col justify-between ${
          winStreak >= 5 ? 'shadow-[0_0_15px_rgba(239,68,68,0.5)]' : ''
        }`}
        whileHover={winStreak >= 3 ? { scale: 1.05 } : {}}
      >
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Current Streak</div>
          <div className={`text-3xl font-bold mt-2 ${
            winStreak >= 5 ? 'text-rose-600 animate-pulse' :
            winStreak >= 3 ? 'text-orange-400' :
            winStreak >= 1 ? 'text-orange-100' :
            'text-zinc-100'
          }`}>{winStreak}</div>
        </div>
        <div className="text-xs text-zinc-600 mt-1">Consecutive wins</div>
      </motion.div>

      {/* Card 5: Inactivity */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-4 flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Inactivity</div>
          <div className={`text-3xl font-bold mt-2 ${daysSinceLastMatch !== null && daysSinceLastMatch > 120 ? 'text-amber-500' : 'text-zinc-100'}`}>
            {daysSinceLastMatch !== null ? `${daysSinceLastMatch}` : 'N/A'}
          </div>
        </div>
        <div className="text-xs text-zinc-600 mt-1">Days since last match</div>
      </div>

      {/* Card 6: Match Dominance */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-4 flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Match Dominance</div>
          <div className="flex items-baseline gap-2 mt-2">
            {stats?.dominance_score !== undefined && stats?.dominance_score !== null ? (
              <div className={`text-3xl font-bold ${stats.dominance_score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {stats.dominance_score >= 0 ? `+${stats.dominance_score}` : stats.dominance_score}
              </div>
            ) : (
              <div className="text-3xl font-bold text-zinc-500">N/A</div>
            )}
            <div className="text-xs text-zinc-500">pts / set</div>
          </div>
        </div>
        
        {stats?.dominance_score !== undefined && stats?.dominance_score !== null && (
          <div className="mt-2">
            <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden relative">
              <div 
                className={`h-full ${stats.dominance_score >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`}
                style={{ 
                  width: `${Math.min(50, Math.abs(stats.dominance_score / 21) * 50)}%`,
                  marginLeft: stats.dominance_score >= 0 ? '50%' : `${50 - Math.min(50, Math.abs(stats.dominance_score / 21) * 50)}%`
                }}
              />
            </div>
            <div className="flex justify-between text-xs text-zinc-600 mt-1">
              <span>-21</span>
              <span>0</span>
              <span>+21</span>
            </div>
          </div>
        )}
      </div>

      {/* Card 7: Optimal Pairings / Rivals */}
      {['MD', 'WD', 'XD'].includes(event) ? (
        <div className="bg-neutral-950 border border-white/5 rounded-lg p-4 col-span-1 md:col-span-2 relative overflow-hidden">
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest relative z-20">Optimal Pairings</div>
          {(stats?.synergy_list?.length || 0) > 0 ? (
            <>
              <BorderBeam colorFrom="#a78bfa" colorTo="#fb7185" duration={8} />
              
              <motion.div 
                className="absolute inset-0 bg-[radial-gradient(circle_at_center,#a78bfa10,transparent_70%)]"
                animate={{ opacity: [0.3, 0.6, 0.3] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              />
              
              <div className="mt-4 space-y-3 relative z-20">
              {stats?.synergy_list?.slice(0, 2).map((p, index: number) => (
                <div key={p.partner_id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div>
                      <div className={`text-sm font-bold ${index === 0 ? 'text-violet-400' : 'text-rose-400'}`}>
                        #{index + 1} {p.partner_name}
                      </div>
                      <div className="text-xs text-zinc-500">Partner</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-zinc-500 uppercase font-mono">Synergy</div>
                    <div className="text-lg font-bold text-zinc-200">
                      {p.synergy?.toFixed(2)}{" "}
                      <span className="text-sm font-normal text-zinc-500">
                        ({p.total_matches} matches)
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            </>
          ) : (
            <div className="text-xs text-zinc-600 mt-2 relative z-20">No synergy data</div>
          )}
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800/50 rounded-lg p-4 col-span-1 md:col-span-2 relative overflow-hidden">
          <BorderBeam colorFrom="#facc15" colorTo="#cbd5e1" duration={8} />
          <RetroGrid />
          
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest relative z-20">Top Rivals</div>
          {(stats?.opponents?.length || 0) > 0 ? (
            <div className="mt-4 space-y-3 relative z-20">
              {stats?.opponents?.slice(0, 2).map((r, index: number) => (
                <div key={r.opponent_id} className="flex items-center justify-between">
                  <div>
                    <div className={`text-sm font-bold ${index === 0 ? 'text-yellow-400' : 'text-slate-300'}`}>
                      #{index + 1} {r.opponent_name}
                    </div>
                    <div className="text-xs text-zinc-500">{r.total_matches} matches</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold">
                      <span className="text-emerald-400">{r.wins}W</span>
                      <span className="text-zinc-100"> - </span>
                      <span className="text-rose-400">{r.total_matches - r.wins}L</span>
                    </div>
                    <div className="text-xs text-zinc-400 font-mono">{r.win_rate}%</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-zinc-600 mt-2 relative z-20">No rival data</div>
          )}
        </div>
      )}
    </div>
  );
};
