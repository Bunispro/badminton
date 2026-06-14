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
    bwf_rank?: number | null;
    bwf_points?: number | null;
    first_match_date?: string | null;
    last_match_date?: string | null;
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
  loading: boolean;
}

const formatCircuitSpan = (first: string | null | undefined, last: string | null | undefined) => {
  if (!first || !last) return 'N/A';
  const d1 = new Date(first);
  const d2 = new Date(last);
  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return 'N/A';
  
  let years = d2.getFullYear() - d1.getFullYear();
  let months = d2.getMonth() - d1.getMonth();
  let days = d2.getDate() - d1.getDate();
  
  if (days < 0) {
    months -= 1;
    const prevMonth = new Date(d2.getFullYear(), d2.getMonth(), 0);
    days += prevMonth.getDate();
  }
  if (months < 0) {
    years -= 1;
    months += 12;
  }
  
  const parts = [];
  if (years > 0) parts.push(`${years}Y`);
  if (months > 0 || years > 0) parts.push(`${months}M`);
  parts.push(`${days}D`);
  return parts.join(' - ');
};

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase();
};

export const StatsSection = ({ stats, winStreak, daysSinceLastMatch, model, event, loading }: StatsSectionProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Rating */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between col-span-1 border-t-2 border-t-cyan-500">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
            {model === 'elo' ? 'Elo' : model === 'whr' ? 'WHR' : 'BWF'} {model === 'bwf' ? 'Points' : 'Rating'}
          </div>
          {loading ? (
            <div className="h-8 w-24 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="flex items-baseline gap-2 mt-2">
              <div className="text-4xl font-bold text-sky-400 font-mono tracking-tight">
                {stats?.current_rating !== undefined && stats?.current_rating !== null
                  ? Math.round(stats.current_rating + (model === 'whr' ? 1000 : 0))
                  : 'N/A'}
              </div>
              <div className="text-sm text-zinc-500">{model === 'elo' ? 'Elo' : model === 'whr' ? 'WHR' : 'BWF'}</div>
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-32 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">Current skill estimate</div>
        )}
      </div>

      {/* Card 2: Rank */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between col-span-1 border-t-2 border-t-emerald-500">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Rank</div>
          {loading ? (
            <div className="h-8 w-20 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-4xl font-bold text-emerald-400 mt-2 font-mono tracking-tight">#{stats?.current_rank || 'N/A'}</div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-36 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          stats?.current_rank && stats?.total_players && stats?.total_players > 0 ? (
            <div>
              <div className="text-sm font-bold text-emerald-600">
                Top {Math.max(0.1, Math.round((stats.current_rank / stats.total_players) * 100))}%
              </div>
              <div className="text-xs text-zinc-600">of {stats.total_players} players</div>
            </div>
          ) : (
            <div className="text-xs text-zinc-600">Rank in category</div>
          )
        )}
      </div>

      {/* Card 3: Win Rate */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Win Rate</div>
          {loading ? (
            <div className="h-8 w-16 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-3xl font-bold text-zinc-100 mt-2 font-mono tracking-tight">{stats?.win_rate}%</div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-28 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600 font-mono">{stats?.wins} Wins / {stats?.total_matches} Matches</div>
        )}
      </div>

      {/* Card 4: Win Streak */}
      <motion.div 
        className={`bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between ${
          !loading && winStreak >= 5 ? 'shadow-[0_0_15px_rgba(239,68,68,0.5)]' : ''
        }`}
        whileHover={!loading && winStreak >= 3 ? { scale: 1.05 } : {}}
      >
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Current Streak</div>
          {loading ? (
            <div className="h-8 w-12 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className={`text-3xl font-bold mt-2 font-mono tracking-tight ${
              winStreak >= 5 ? 'text-rose-600 animate-pulse' :
              winStreak >= 3 ? 'text-orange-400' :
              winStreak >= 1 ? 'text-orange-100' :
              'text-zinc-100'
            }`}>{winStreak}</div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-24 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">Consecutive wins</div>
        )}
      </motion.div>

      {/* Card 5: Inactivity */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Inactivity</div>
          {loading ? (
            <div className="h-8 w-16 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className={`text-3xl font-bold mt-2 font-mono tracking-tight ${daysSinceLastMatch !== null && daysSinceLastMatch > 120 ? 'text-amber-500' : 'text-zinc-100'}`}>
              {daysSinceLastMatch !== null ? `${daysSinceLastMatch}` : 'N/A'}
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-28 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">Days since last match</div>
        )}
      </div>

      {/* Card 6: Match Dominance */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Match Dominance</div>
          {loading ? (
            <div className="h-8 w-20 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="flex items-baseline gap-2 mt-2">
              {stats?.dominance_score !== undefined && stats?.dominance_score !== null ? (
                <div className={`text-3xl font-bold font-mono tracking-tight ${stats.dominance_score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {stats.dominance_score >= 0 ? `+${stats.dominance_score}` : stats.dominance_score}
                </div>
              ) : (
                <div className="text-3xl font-bold text-zinc-500 font-mono tracking-tight">N/A</div>
              )}
              <div className="text-xs text-zinc-500">pts / set</div>
            </div>
          )}
        </div>
        
        {loading ? (
          <div className="h-3 w-32 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          stats?.dominance_score !== undefined && stats?.dominance_score !== null ? (
            <div>
              <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden relative">
                <div 
                  className={`h-full ${stats.dominance_score >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`}
                  style={{ 
                    width: `${Math.min(50, Math.abs(stats.dominance_score / 21) * 50)}%`,
                    marginLeft: stats.dominance_score >= 0 ? '50%' : `${50 - Math.min(50, Math.abs(stats.dominance_score / 21) * 50)}%`
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5 font-mono">
                <span>-21</span>
                <span>0</span>
                <span>+21</span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-zinc-600">Points dominance per set</div>
          )
        )}
      </div>

      {/* Card 7: Optimal Pairings / Rivals */}
      {['MD', 'WD', 'XD'].includes(event) ? (
        <div className="bg-neutral-950 border border-white/5 rounded-lg p-5 h-[140px] col-span-1 md:col-span-2 relative overflow-hidden">
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest relative z-20">Optimal Pairings</div>
          {loading ? (
            <div className="mt-4 space-y-3 relative z-20">
              <div className="h-4 w-48 bg-zinc-800/60 animate-pulse rounded" />
              <div className="h-4 w-40 bg-zinc-800/60 animate-pulse rounded" />
            </div>
          ) : (stats?.synergy_list?.length || 0) > 0 ? (
            <>
              <BorderBeam colorFrom="#a78bfa" colorTo="#fb7185" duration={8} />
              <motion.div 
                className="absolute inset-0 bg-[radial-gradient(circle_at_center,#a78bfa10,transparent_70%)]"
                animate={{ opacity: [0.3, 0.6, 0.3] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              />
              
              <div className="mt-2 space-y-2 relative z-20">
                {stats?.synergy_list?.slice(0, 2).map((p, index: number) => (
                  <div key={p.partner_id} className="flex items-center justify-between text-xs">
                    <div>
                      <div className={`font-bold ${index === 0 ? 'text-violet-400' : 'text-rose-400'}`}>
                        #{index + 1} {p.partner_name}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-zinc-200 font-bold font-mono">{p.synergy?.toFixed(2)}</span>
                      <span className="text-[10px] text-zinc-500 font-mono ml-1">({p.total_matches} matches)</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-xs text-zinc-600 mt-4 relative z-20">No synergy data</div>
          )}
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800/50 rounded-lg p-5 h-[140px] col-span-1 md:col-span-2 relative overflow-hidden">
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest relative z-20">Top Rivals</div>
          {loading ? (
            <div className="mt-4 space-y-3 relative z-20">
              <div className="h-4 w-48 bg-zinc-800/60 animate-pulse rounded" />
              <div className="h-4 w-40 bg-zinc-800/60 animate-pulse rounded" />
            </div>
          ) : (stats?.opponents?.length || 0) > 0 ? (
            <>
              <BorderBeam colorFrom="#facc15" colorTo="#cbd5e1" duration={8} />
              <RetroGrid />
              <div className="mt-2 space-y-2 relative z-20">
                {stats?.opponents?.slice(0, 2).map((r, index: number) => (
                  <div key={r.opponent_id} className="flex items-center justify-between text-xs">
                    <div>
                      <div className={`font-bold ${index === 0 ? 'text-yellow-400' : 'text-slate-300'}`}>
                        #{index + 1} {r.opponent_name}
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <span className="text-emerald-400 font-bold">{r.wins}W</span>
                      <span className="text-zinc-500"> - </span>
                      <span className="text-rose-400 font-bold">{r.total_matches - r.wins}L</span>
                      <span className="text-[10px] text-zinc-500 ml-1">({r.win_rate}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-xs text-zinc-600 mt-4 relative z-20">No rival data</div>
          )}
        </div>
      )}

      {/* Card 8: Total Matches */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Total Matches</div>
          {loading ? (
            <div className="h-8 w-16 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-3xl font-bold text-zinc-100 mt-2 font-mono tracking-tight">
              {stats?.total_matches !== undefined && stats?.total_matches !== null ? stats.total_matches : 'N/A'}
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-28 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">BWF circuit match count</div>
        )}
      </div>

      {/* Card 9: Longevity in BWF Circuit */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">Circuit Longevity</div>
          {loading ? (
            <div className="h-8 w-32 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-2xl font-bold text-zinc-100 mt-2 font-mono tracking-tight">
              {formatCircuitSpan(stats?.first_match_date, stats?.last_match_date)}
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-36 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600 truncate font-mono">
            {stats?.first_match_date && stats?.last_match_date ? (
              `${formatDate(stats.first_match_date)} - ${formatDate(stats.last_match_date)}`
            ) : (
              'Career match span'
            )}
          </div>
        )}
      </div>

      {/* Card 10: Current BWF Ranking */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between border-t-2 border-t-yellow-500/80">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">BWF World Rank</div>
          {loading ? (
            <div className="h-8 w-16 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-3xl font-bold text-yellow-400 mt-2 font-mono tracking-tight">
              {stats?.bwf_rank ? `#${stats.bwf_rank}` : 'N/A'}
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-32 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">Official BWF rank in category</div>
        )}
      </div>

      {/* Card 11: BWF Points */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-5 h-[140px] flex flex-col justify-between">
        <div>
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">BWF World Points</div>
          {loading ? (
            <div className="h-8 w-24 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-3xl font-bold text-zinc-100 mt-2 font-mono tracking-tight">
              {stats?.bwf_points !== undefined && stats?.bwf_points !== null ? stats.bwf_points.toLocaleString() : 'N/A'}
            </div>
          )}
        </div>
        {loading ? (
          <div className="h-3 w-24 bg-zinc-800/40 animate-pulse rounded" />
        ) : (
          <div className="text-xs text-zinc-600">Official ranking points</div>
        )}
      </div>
    </div>
  );
};
