'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShinyButton } from '@/components/magicui/shiny-button';
import { NumberTicker } from '@/components/magicui/number-ticker';
import { BorderBeam } from '@/components/magicui/border-beam';
import { RetroGrid } from '@/components/magicui/retro-grid';
import { AnimatedBeam } from '@/components/magicui/animated-beam';
import { BentoGrid, BentoCard } from '@/components/magicui/bento-grid';
import { AreaChart } from '@tremor/react';
import Flag from 'react-flagpack';
import 'react-flagpack/dist/style.css';
import { HugeiconsIcon } from '@hugeicons/react';
import { UserGroupIcon, Clock01Icon, ChartLineData01Icon } from '@hugeicons/core-free-icons';
import countryCodes from '@/lib/countryCodes.json';

const chartdata = [
  { date: 'JAN 22', ELO: 1200 },
  { date: 'FEB 22', ELO: 1300 },
  { date: 'MAR 22', ELO: 1250 },
  { date: 'APR 22', ELO: 1400 },
  { date: 'MAY 22', ELO: 1380 },
  { date: 'JUN 22', ELO: 1540 },
];

const customTooltip = (props: any) => {
  const { active, payload, label } = props;
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-lg shadow-lg">
        <p className="text-zinc-500 font-mono text-[10px] uppercase tracking-wider">{label}</p>
        <p className="text-zinc-100 font-mono font-bold text-lg">{payload[0].value}</p>
      </div>
    );
  }
  return null;
};

const getCountryCode = (countryName: string) => {
  return (countryCodes as Record<string, string>)[countryName] || null;
};

export default function Home() {
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/leaderboard?event=MS&model=whr&mode=current&limit=20')
      .then(res => res.json())
      .then(data => {
        setLeaderboard(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch leaderboard:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="relative min-h-[80vh] flex flex-col items-center justify-center space-y-12 py-12 overflow-hidden">
      {/* Background Pattern */}
      <RetroGrid />

      {/* CSS Overrides for Tremor/Recharts */}
      <style jsx global>{`
        .recharts-cartesian-axis-tick-value {
          font-family: var(--font-geist-mono), monospace !important;
          font-size: 10px !important;
          fill: #71717a !important; /* zinc-500 */
          letter-spacing: 0.05em;
        }
        .recharts-cartesian-grid-horizontal line,
        .recharts-cartesian-grid-vertical line {
          stroke: rgba(39, 39, 42, 0.5) !important; /* zinc-800/50 */
        }
        /* Target the line specifically */
        .recharts-area-curve {
          stroke: #38bdf8 !important; /* sky-400 */
          stroke-width: 2px !important;
        }
        /* Target the fill specifically and remove its stroke */
        .recharts-area-area {
          stroke: none !important;
          fill: #38bdf8 !important; /* sky-400 */
          fill-opacity: 0.05 !important;
        }
        /* Fallback for general curves if the above classes don't match */
        .recharts-curve {
          stroke-width: 2px;
        }
      `}</style>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-4 text-center z-10"
      >
        <span className="text-sm font-semibold uppercase tracking-wider text-cyan-400">Component Test Area</span>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-zinc-100">
          Advanced Features <span className="text-cyan-400">Integration</span>
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
          We have implemented custom versions of Magic UI components and added Tremor, Flagpack, and Hugeicons examples.
        </p>
        <div className="flex gap-4 justify-center pt-4">
          <ShinyButton>
            Shiny Button
          </ShinyButton>
        </div>
      </motion.div>

      {/* 1. Animated Beam Section */}
      <div className="w-full max-w-5xl space-y-4 z-10">
        <h2 className="text-2xl font-bold text-zinc-100 text-center">1. Animated Beam (Match Engine)</h2>
        <AnimatedBeam />
      </div>

      {/* 2. Bento Grid & 3. Number Ticker & 4. Border Beam */}
      <div className="w-full max-w-5xl space-y-4 z-10">
        <h2 className="text-2xl font-bold text-zinc-100 text-center">2. Bento Grid & Counters</h2>
        <BentoGrid>
          {/* Large Card for Trend (Tremor Chart) */}
          <BentoCard className="md:col-span-2 min-h-[300px]">
            <div>
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">ELO Progression</h3>
              <p className="text-sm text-zinc-400">Simulated trend chart with custom grid and labels.</p>
            </div>
            <div className="h-48 mt-4">
              <AreaChart
                className="h-full"
                data={chartdata}
                index="date"
                categories={["ELO"]}
                colors={["sky"]}
                showLegend={false}
                showGridLines={true}
                showYAxis={true}
                showXAxis={true}
                customTooltip={customTooltip}
              />
            </div>
          </BentoCard>

          {/* Small Card for Rank */}
          <BentoCard>
            <div>
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">Current Rank</h3>
              <p className="text-sm text-zinc-400">Your standing.</p>
            </div>
            <div className="mt-auto text-center">
              <span className="text-5xl font-bold font-mono text-cyan-400">#1</span>
            </div>
          </BentoCard>

          {/* Top Tier Player with Border Beam */}
          <BentoCard className="relative md:col-span-1">
            <BorderBeam duration={15} />
            <div className="relative z-10 h-full flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-semibold text-zinc-100 mb-2">Top Tier Player</h3>
                <p className="text-sm text-zinc-400">King of the Court.</p>
              </div>
              <div className="mt-auto">
                <span className="text-xl font-bold text-zinc-100">KhaiProVip</span>
                <div className="text-sm text-zinc-500">Uncertainty: ± 12</div>
              </div>
            </div>
          </BentoCard>

          {/* Hugeicons Example */}
          <BentoCard className="md:col-span-2">
            <div>
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">Hugeicons & Metrics</h3>
              <p className="text-sm text-zinc-400">Premium icons for badminton metrics.</p>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="bg-zinc-800/50 p-4 rounded-lg border border-zinc-800 flex flex-col items-center gap-2">
                <HugeiconsIcon icon={UserGroupIcon} size={24} color="#22d3ee" strokeWidth={1.5} />
                <span className="text-xs text-zinc-400">Synergy</span>
              </div>
              <div className="bg-zinc-800/50 p-4 rounded-lg border border-zinc-800 flex flex-col items-center gap-2">
                <HugeiconsIcon icon={Clock01Icon} size={24} color="#f43f5e" strokeWidth={1.5} />
                <span className="text-xs text-zinc-400">Inactivity</span>
              </div>
              <div className="bg-zinc-800/50 p-4 rounded-lg border border-zinc-800 flex flex-col items-center gap-2">
                <HugeiconsIcon icon={ChartLineData01Icon} size={24} color="#10b981" strokeWidth={1.5} />
                <span className="text-xs text-zinc-400">Margin</span>
              </div>
            </div>
          </BentoCard>
        </BentoGrid>
      </div>

      {/* Leaderboard Table Section */}
      <div className="w-full max-w-5xl space-y-4 z-10">
        <h2 className="text-2xl font-bold text-zinc-100 text-center">3. Leaderboard Table (Real Data)</h2>
        <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-lg overflow-hidden">
          {loading ? (
            <div className="p-6 text-center text-zinc-400">Loading leaderboard...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-zinc-400">
                <thead className="bg-zinc-800/50 text-zinc-500 uppercase text-xs">
                  <tr>
                    <th className="px-6 py-3 sticky left-0 bg-zinc-900/50 z-20">Rank</th>
                    <th className="px-6 py-3 sticky left-[4rem] bg-zinc-900/50 z-20">Player</th>
                    <th className="px-6 py-3">Rating</th>
                    <th className="px-6 py-3">Trend</th>
                    <th className="px-6 py-3">Form</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((player, index) => {
                    const countryCode = getCountryCode(player.country);
                    return (
                      <tr key={player.player_id} className="border-t border-zinc-800 hover:bg-zinc-800/30 transition-colors">
                        <td className="px-6 py-4 font-bold text-zinc-100 sticky left-0 bg-zinc-950/80 backdrop-blur-sm z-10">#{index + 1}</td>
                        <td className="px-6 py-4 sticky left-[4rem] bg-zinc-950/80 backdrop-blur-sm z-10">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-zinc-100">{player.name}</span>
                            {countryCode ? (
                              <div className="grayscale-[0.1] brightness-[0.9] rounded-sm opacity-90 hover:grayscale-0 hover:opacity-100 transition-all">
                                <Flag code={countryCode.toUpperCase()} size="S" />
                              </div>
                            ) : (
                              <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 002 2h2.945M8 3.935A9 9 0 0116.065 3.055M8 3.935A9 9 0 003.055 11M3.055 11a9 9 0 0013.01 10.01M16.065 3.055a9 9 0 013.99 3.99M16.065 3.055A9 9 0 0019.945 11H18a2 2 0 01-2-2V7a2 2 0 00-2-2h-1.5a2.5 2.5 0 01-2.455-2.455z"></path></svg>
                            )}
                          </div>
                          {/* Recent Matches */}
                          <div className="flex flex-col gap-1 mt-1">
                            {player.recent_matches?.slice(0, 3).map((match: any) => {
                              const isSide1 = match.side1.some((p: any) => p.id === player.player_id);
                              const won = (isSide1 && match.winner_side === 1) || (!isSide1 && match.winner_side === 2);
                              const opponent = isSide1 ? match.side2 : match.side1;
                              const opponentName = opponent.map((p: any) => p.name).join(' / ');
                              
                              return (
                                <div key={match.match_id} className="text-xs text-zinc-500 flex items-center gap-1 group relative cursor-pointer">
                                  <span className={won ? "text-emerald-500 font-bold" : "text-rose-500 font-bold"}>
                                    {won ? "W" : "L"}
                                  </span>
                                  <span className="truncate max-w-[150px]">{opponentName}</span>
                                  
                                  {/* Tooltip */}
                                  <div className="absolute left-0 bottom-full mb-1 opacity-0 group-hover:opacity-100 transition-opacity bg-zinc-900 border border-zinc-800 p-2 rounded shadow-lg z-30 w-64 pointer-events-none">
                                    <div className="text-xs text-zinc-100 font-bold">{match.tournament}</div>
                                    <div className="text-xs text-cyan-400 font-mono">{match.score}</div>
                                    <div className="text-xs text-zinc-400 mt-1">
                                      {match.side1.map((p: any) => p.name).join('/')} vs {match.side2.map((p: any) => p.name).join('/')}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </td>
                        <td className="px-6 py-4 font-mono text-zinc-100">
                          <NumberTicker value={player.rating} />
                        </td>
                        <td className="px-6 py-4">
                          <span className={player.change >= 0 ? "text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded text-sm font-bold" : "text-rose-500 bg-rose-500/10 px-2 py-0.5 rounded text-sm font-bold"}>
                            {player.change >= 0 ? `+${player.change}` : player.change}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {/* Sparkline placeholder based on change */}
                          <svg className={`w-24 h-6 ${player.change >= 0 ? "text-emerald-500" : "text-rose-500"}`} viewBox="0 0 100 20">
                            <polyline
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              points={player.change >= 0 ? "0,15 20,10 40,12 60,5 80,8 100,2" : "0,5 20,8 40,5 60,15 80,12 100,18"}
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
