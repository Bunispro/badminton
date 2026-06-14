'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { RatingGraph } from '@/components/charts/rating-graph';
import { API_BASE_URL } from '@/lib/api';
import { useThrottledCallback } from '@/hooks/use-throttled-callback';

// Extracted Components
import { getCountryCode } from './utils';
import { PlayerHeader } from './components/player-header';
import { StatsSection } from './components/stats-section';
import { MatchFlipCard } from './components/match-flip-card';

interface PlayerMetadata {
  name: string;
  country: string;
  disciplines: string[];
}

interface PlayerStats {
  current_rating?: number;
  current_rank?: number;
  total_players?: number;
  win_rate?: number;
  wins?: number;
  total_matches?: number;
  dominance_score?: number;
  inactivity_threshold?: number;
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
}

interface HistoryPoint {
  rating: number;
  date: string;
  rank?: number;
  points?: number;
}

interface MatchParticipant {
  id: string;
  name: string;
}

interface Match {
  match_id: string;
  date: string;
  event: string;
  model: string;
  winner_side: number;
  side1: MatchParticipant[];
  side2: MatchParticipant[];
  score?: string;
  tournament?: string;
  duration?: number;
  side1_rating?: number;
  side2_rating?: number;
  predicted_prob?: number;
  actual?: number;
}

export default function PlayerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const [player, setPlayer] = useState<PlayerMetadata | null>(null);
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [allMatches, setAllMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [event, setEvent] = useState('MS');
  const [hasSetDefaultEvent, setHasSetDefaultEvent] = useState(false);
  const [model, setModel] = useState('elo');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [historyPeriod, setHistoryPeriod] = useState('all');

  const handleSetEvent = useThrottledCallback((ev: string) => setEvent(ev), 200);
  const handleSetModel = useThrottledCallback((m: string) => setModel(m), 200);
  const handleSetHistoryPeriod = useThrottledCallback((p: string) => {
    setHistoryPeriod(p);
    setStartDate('');
    setEndDate('');
  }, 200);
  const handleClearDates = useThrottledCallback(() => {
    setStartDate('');
    setEndDate('');
  }, 200);

  // Reset default event flag when player ID changes
  useEffect(() => {
    setHasSetDefaultEvent(false);
  }, [id]);

  // Clear manual date filters when event or model changes to prevent mismatched bounds
  useEffect(() => {
    const timer = setTimeout(() => {
      setStartDate('');
      setEndDate('');
    }, 0);
    return () => clearTimeout(timer);
  }, [event, model]);

  // Auto-select first available discipline with most matches when player data loads
  useEffect(() => {
    if (player?.disciplines && player.disciplines.length > 0 && !hasSetDefaultEvent) {
      setEvent(player.disciplines[0]);
      setHasSetDefaultEvent(true);
    }
  }, [player, hasSetDefaultEvent]);

  // Auto-select first available discipline if current selection is not valid for this player
  useEffect(() => {
    if (player?.disciplines && player.disciplines.length > 0) {
      if (!player.disciplines.includes(event)) {
        setEvent(player.disciplines[0]);
      }
    }
  }, [player, event]);

  const isSharpView = useMemo(() => {
    if (historyPeriod === '1m' || historyPeriod === '3m' || historyPeriod === '6m') {
      return true;
    }
    if (startDate || endDate) {
      const start = startDate ? new Date(startDate) : (history.length > 0 ? new Date(history[0].date) : new Date());
      const end = endDate ? new Date(endDate) : new Date();
      const diffDays = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays <= 183) {
        return true;
      }
    }
    return false;
  }, [historyPeriod, startDate, endDate, history]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setOffset(0);
    setHasMore(true);
    try {
      const historyUrl = model === 'bwf'
        ? `${API_BASE_URL}/api/player/${id}/bwf-history?event=${event}`
        : `${API_BASE_URL}/api/player/${id}/history?event=${event}&model=${model}&start_date=${startDate}&end_date=${endDate}`;

      const [pRes, sRes, hRes, mRes, amRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/player/${id}`),
        fetch(`${API_BASE_URL}/api/player/${id}/statistics?event=${event}&model=${model}`),
        fetch(historyUrl),
        fetch(`${API_BASE_URL}/api/player/${id}/matches?event=${event}&model=${model}&offset=0&start_date=${startDate}&end_date=${endDate}`),
        fetch(`${API_BASE_URL}/api/player/${id}/matches?event=${event}&model=${model}&limit=1000&include_ratings=false`)
      ]);
      
      if (pRes.ok) setPlayer(await pRes.json());
      if (sRes.ok) setStats(await sRes.json());
      if (hRes.ok) {
        const hData = await hRes.json();
        if (model === 'bwf') {
          // Map BWF points to rating so RatingGraph can render it out of the box
          setHistory(hData.map((x: { date: string; points: number; rank: number }) => ({
            date: x.date,
            rating: x.points,
            rank: x.rank,
            points: x.points
          })));
        } else {
          setHistory(hData);
        }
      }
      if (mRes.ok) {
        const mData = await mRes.json();
        setMatches(mData);
        if (mData.length < 20) setHasMore(false);
      }
      if (amRes.ok) {
        setAllMatches(await amRes.json());
      }
    } catch (error) {
      console.error("Fetch failed:", error);
    } finally {
      setLoading(false);
    }
  }, [id, event, model, startDate, endDate]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchData]);

  const loadMoreMatches = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextOffset = offset + 20;
      const res = await fetch(`${API_BASE_URL}/api/player/${id}/matches?event=${event}&model=${model}&offset=${nextOffset}&start_date=${startDate}&end_date=${endDate}`);
      if (res.ok) {
        const data = await res.json();
        if (data.length === 0) {
          setHasMore(false);
        } else {
          setMatches(prev => [...prev, ...data]);
          setOffset(nextOffset);
        }
      }
    } catch (error) {
      console.error("Load more failed:", error);
    } finally {
      setLoadingMore(false);
    }
  }, [id, event, model, startDate, endDate, offset, loadingMore, hasMore]);



  useEffect(() => {
    const handleScroll = () => {
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
        loadMoreMatches();
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [loadMoreMatches]);

  // Analytical Memoizations
  const winStreak = useMemo(() => {
    let streak = 0;
    for (const match of allMatches) {
      const isSide1 = match.side1?.some((p: MatchParticipant) => p.id === id);
      const won = (isSide1 && match.winner_side === 1) || (!isSide1 && match.winner_side === 2);
      if (won) streak++; else break;
    }
    return streak;
  }, [allMatches, id]);

  const daysSinceLastMatch = useMemo(() => {
    const lastDate = allMatches[0]?.date;
    if (!lastDate) return null;
    return Math.floor((new Date().getTime() - new Date(lastDate).getTime()) / (1000 * 60 * 60 * 24));
  }, [allMatches]);

  const countryCode = useMemo(() => player?.country ? getCountryCode(player.country) : null, [player]);

  const filteredHistory = useMemo(() => {
    if (!history || history.length === 0) return [];
    if (historyPeriod === 'all') return history;
    
    // Find the latest date in history as the base date
    const latestDateStr = history[history.length - 1].date;
    const latestDate = new Date(latestDateStr);
    
    let daysToSubtract = 30;
    if (historyPeriod === '3m') daysToSubtract = 90;
    else if (historyPeriod === '6m') daysToSubtract = 180;
    else if (historyPeriod === '1y') daysToSubtract = 365;
    
    const cutoffTime = latestDate.getTime() - (daysToSubtract * 24 * 60 * 60 * 1000);
    return history.filter(h => new Date(h.date).getTime() >= cutoffTime);
  }, [history, historyPeriod]);

  const chartData = useMemo(() => {
    if (filteredHistory.length === 0) return [];
    
    // Find peak rating in filteredHistory
    let peakIndex = -1;
    let maxRating = -Infinity;
    let minRank = Infinity;
    
    for (let i = 0; i < filteredHistory.length; i++) {
      if (model === 'bwf') {
        const rank = filteredHistory[i].rank || Infinity;
        if (rank < minRank) {
          minRank = rank;
          peakIndex = i;
        } else if (rank === minRank) {
          if (filteredHistory[i].rating > (filteredHistory[peakIndex]?.rating || 0)) {
            peakIndex = i;
          }
        }
      } else {
        if (filteredHistory[i].rating > maxRating) {
          maxRating = filteredHistory[i].rating;
          peakIndex = i;
        }
      }
    }
    
    return filteredHistory.map((h, index) => {
      const isPeak = index === peakIndex;
      return {
        ...h,
        rating: h.rating + (model === 'whr' ? 1000 : 0),
        timestamp: new Date(h.date).getTime(),
        isPeak: isPeak,
        color: isPeak ? "#38bdf8" : "#38bdf8", // Always sky blue
        r: isPeak ? 5 : 2
      };
    });
  }, [filteredHistory, model]);

  return (
    <div className="min-h-screen bg-zinc-950 text-white font-sans relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(24,24,27,0.8)_0%,_rgba(0,0,0,1)_80%)] z-0" />
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 py-12">
        <Link href="/leaderboard" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-300 transition-colors mb-8">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
          Back to Leaderboard
        </Link>

          <div className="space-y-8">
            <PlayerHeader player={player} stats={stats} countryCode={countryCode} daysSinceLastMatch={daysSinceLastMatch} loading={loading && !player} />

            <div className="w-full flex flex-wrap gap-4 items-center justify-between bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 backdrop-blur-sm">
              <div className="flex gap-2">
                {player?.disciplines?.map((ev: string) => (
                  <button
                    key={ev}
                    onClick={() => handleSetEvent(ev)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${event === ev ? "bg-zinc-100 text-zinc-900 font-bold" : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"}`}
                  >
                    <motion.span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent" initial={{ x: '-100%' }} whileHover={{ x: '100%' }} transition={{ duration: 0.5, ease: 'easeInOut' }} />
                    <span className="relative z-10">{ev}</span>
                  </button>
                ))}
              </div>

              <div className="flex gap-2">
                <button onClick={() => handleSetModel('elo')} className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${model === 'elo' ? "bg-zinc-100 text-zinc-900 font-bold" : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"}`}>
                  <span className="relative z-10">Elo Model</span>
                </button>
                <button onClick={() => handleSetModel('whr')} className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${model === 'whr' ? "bg-zinc-100 text-zinc-900 font-bold" : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"}`}>
                  <span className="relative z-10">WHR Model</span>
                </button>
                <button onClick={() => handleSetModel('bwf')} className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${model === 'bwf' ? "bg-zinc-100 text-zinc-900 font-bold" : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"}`}>
                  <span className="relative z-10">Official BWF</span>
                </button>
              </div>
            </div>
 
            <StatsSection stats={stats} winStreak={winStreak} daysSinceLastMatch={daysSinceLastMatch} model={model} event={event} loading={loading} />
 
            <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold text-zinc-100">Rating History</h2>
                <div className="flex gap-2">
                  {['1m', '3m', '6m', '1y', 'all'].map(p => (
                    <button 
                      key={p} 
                      onClick={() => handleSetHistoryPeriod(p)}
                      className={`px-2.5 py-1 text-[10px] rounded transition-all font-semibold uppercase tracking-wider ${historyPeriod === p ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white'}`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
              <div className="h-64 w-full">
                {loading && history.length === 0 ? (
                  <div className="h-full w-full bg-zinc-950/40 rounded-lg flex items-center justify-center animate-pulse border border-zinc-800/30">
                    <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest">Loading Rating History...</div>
                  </div>
                ) : (
                  <RatingGraph chartData={chartData} isSharpView={isSharpView} matches={allMatches} history={filteredHistory} id={id} model={model} />
                )}
              </div>
            </div>

            <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg">
              <div className="px-6 py-4 border-b border-zinc-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <h2 className="text-lg font-bold text-zinc-100">Match History</h2>
                
                {/* Elegant Date Filter Bar */}
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest">From</span>
                    <input 
                      type="date" 
                      value={startDate} 
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        setHistoryPeriod('all');
                      }}
                      className="px-3 py-1.5 text-xs bg-zinc-950/60 text-zinc-100 border border-zinc-800/80 rounded-md focus:outline-none focus:border-sky-500 transition-colors font-mono cursor-pointer"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest">To</span>
                    <input 
                      type="date" 
                      value={endDate} 
                      onChange={(e) => {
                        setEndDate(e.target.value);
                        setHistoryPeriod('all');
                      }}
                      className="px-3 py-1.5 text-xs bg-zinc-950/60 text-zinc-100 border border-zinc-800/80 rounded-md focus:outline-none focus:border-sky-500 transition-colors font-mono cursor-pointer"
                    />
                  </div>
                  {(startDate || endDate) && (
                    <button 
                      onClick={handleClearDates}
                      className="px-2.5 py-1.5 text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-md transition-colors"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              
              {loading && matches.length === 0 ? (
                <div className="p-4 pb-12 space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-24 w-full bg-zinc-900/30 border border-zinc-800/40 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : matches.length > 0 ? (
                <div className="p-4 pb-12 space-y-3">
                  {matches.map((match) => {
                    const isSide1 = match.side1?.some((p: MatchParticipant) => p.id === id);
                    const won = (isSide1 && match.winner_side === 1) || (!isSide1 && match.winner_side === 2);
                    return (
                      <MatchFlipCard key={match.match_id} match={match} won={won} isSide1={isSide1} id={id} model={model} />
                    );
                  })}
                </div>
              ) : (
                <div className="p-24 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">No match records found</div>
              )}
            </div>
          </div>
      </div>
    </div>
  );
}
