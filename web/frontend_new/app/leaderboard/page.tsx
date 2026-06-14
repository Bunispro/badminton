'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createPortal } from 'react-dom';
import { RetroGrid } from '@/components/magicui/retro-grid';
import { Flag } from '@/components/ui/flag';
import { API_BASE_URL } from '@/lib/api';
import countryCodes from '@/lib/countryCodes.json';
import continentMapping from '@/lib/continentMapping.json';
import { Command } from 'cmdk';
import React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { useWindowVirtualizer } from '@tanstack/react-virtual';
import { useThrottledCallback } from '@/hooks/use-throttled-callback';

interface HistoryPoint {
  rating: number;
  date: string;
}

interface LeaderboardPlayer {
  player_id: string;
  name: string;
  country: string;
  rating: number;
  change: number;
  winrate?: number;
  rank_at_peak?: number;
  bwf_rank?: number;
  date: string;
  history?: HistoryPoint[];
  synergy_partner?: {
    player_id: string;
    name: string;
    score: number;
  };
}

const getCountryCode = (countryName: string) => {
  if (!countryName) return null;
  const trimmed = countryName.trim();
  const code = (countryCodes as Record<string, string>)[trimmed] || null;
  if (code === 'UK') return 'GB';
  if (code === 'uk') return 'gb';
  return code;
};

const PlayerCard = React.memo(({
  player,
  index,
  virtualRow,
  isExpanded,
  hideForm,
  mode,
  onToggleExpand,
  measureElement,
  scrollMargin
}: {
  player: LeaderboardPlayer;
  index: number;
  virtualRow: { index: number; start: number };
  isExpanded: boolean;
  hideForm: boolean;
  mode: string;
  onToggleExpand: (id: string) => void;
  measureElement: (element: HTMLElement | null) => void;
  scrollMargin: number;
}) => {
  const playerCountryCode = getCountryCode(player.country);
  const searchParams = useSearchParams();
  const model = searchParams.get('model') || 'elo';

  const points = useMemo(() => {
    const historyData = player.history || [];
    if (historyData.length < 2) return "";
    const ratings = historyData.map((h: HistoryPoint) => h.rating);
    const min = Math.min(...ratings);
    const max = Math.max(...ratings);
    const range = max - min || 1;
    return ratings.map((r: number, i: number) => {
      const x = (i / (ratings.length - 1)) * 100;
      const y = 22 - ((r - min) / range) * 20;
      return `${x},${y}`;
    }).join(" ");
  }, [player.history]);

  return (
    <div 
      ref={measureElement}
      data-index={virtualRow.index}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        transform: `translateY(${virtualRow.start - scrollMargin}px)`,
      }}
    >
      <motion.div 
        className={`relative overflow-hidden hover:bg-zinc-800/40 transition-all cursor-pointer group border-b border-zinc-800/60 px-4 py-3 ${isExpanded ? 'bg-zinc-800/50 shadow-[inset_0_0_20px_rgba(56,189,248,0.05)]' : ''}`}
        onClick={() => {
          onToggleExpand(player.player_id);
        }}
      >
        <div className="grid grid-cols-12 gap-4 items-center z-10 relative">
          {/* Column 1: Rank */}
          <div className="col-span-1 flex items-center justify-center">
            <span className={`font-semibold text-lg ${index < 3 ? "text-white" : "text-zinc-500"}`}>
              {index + 1}
            </span>
          </div>

          {/* Column 2: Player Identity */}
          {(() => {
            const isSeasonalWHRorElo = mode === 'seasonal' && model !== 'bwf';
            return (
              <>
                <div className={`${hideForm ? (isSeasonalWHRorElo ? 'col-span-4' : 'col-span-5') : (isSeasonalWHRorElo ? 'col-span-3' : 'col-span-4')} flex items-center gap-4`}>
                  {playerCountryCode && (
                    <div className="flex-shrink-0 grayscale-[0.2] opacity-80 group-hover:grayscale-0 group-hover:opacity-100 transition-all w-8 h-6 overflow-hidden rounded-sm flex items-center justify-center bg-zinc-800">
                      <Flag code={playerCountryCode} className="w-full h-full" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="font-bold text-zinc-100 text-lg break-words whitespace-normal line-clamp-2 flex items-center gap-2">
                      {player.name}
                    </div>
                    <div className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-black font-mono">
                      {player.country}
                    </div>
                  </div>
                </div>

                {/* Column 2.5: BWF Rank (Seasonal WHR/Elo only) */}
                {isSeasonalWHRorElo && (
                  <div className="col-span-1 text-center">
                    <span className="font-mono text-zinc-300 font-bold text-lg">
                      {player.bwf_rank ? `#${player.bwf_rank}` : '--'}
                    </span>
                  </div>
                )}
              </>
            );
          })()}

          <div className="col-span-2 text-center">
            <div className="text-xl font-bold text-sky-400 tracking-tight">
              {Math.round(player.rating + (model === 'whr' ? 1000 : 0))}
            </div>
          </div>

          {/* Column 4: Trend / Win Rate */}
          <div className="col-span-2 text-center flex flex-col items-center justify-center">
            {mode === 'seasonal' ? (
              <div className={`font-mono font-black text-lg ${player.change > 0 ? 'text-emerald-400' : player.change < 0 ? 'text-rose-400' : 'text-zinc-500'}`}>
                {player.change > 0 ? '+' : ''}{typeof player.change === 'number' ? player.change.toFixed(1) : '0.0'}
              </div>
            ) : (
              <div className="font-mono text-zinc-100 font-black text-lg">
                {player.winrate ? `${Math.round(player.winrate)}%` : '--'}
              </div>
            )}
          </div>

          {/* Column 5: Form Sparkline / Peak Global Rank */}
          {!hideForm && (
            <div className="col-span-1 flex flex-col items-center justify-center">
              {mode === 'seasonal' ? (
                points.length > 0 ? (
                  <svg className="w-12 h-5 text-sky-400/50 group-hover:text-sky-400 transition-colors" viewBox="0 0 100 24">
                    <polyline fill="none" stroke="currentColor" strokeWidth="2.5" points={points} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <span className="text-[8px] text-zinc-800 font-black tracking-widest uppercase">No Data</span>
                )
              ) : (
                <div className="font-mono text-zinc-100 font-black text-lg">
                  {player.rank_at_peak ? `#${player.rank_at_peak}` : '--'}
                </div>
              )}
            </div>
          )}

          {/* Column 6: Date */}
          <div className="col-span-2 flex items-center justify-center">
            <div className="text-center font-mono text-sm text-zinc-100 font-black tracking-tighter brightness-125">
              {player.date?.split('-').slice(0, 2).join('-')}
            </div>
          </div>
        </div>

      </motion.div>
    </div>
  );
});
PlayerCard.displayName = 'PlayerCard';

function LeaderboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const model = searchParams.get('model') || 'elo';
  const mode = searchParams.get('mode') || 'seasonal';
  const hideForm = searchParams.get('hideForm') === 'true';

  const [leaderboard, setLeaderboard] = useState<LeaderboardPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);
  const [loadingMore, setLoadingMore] = useState(false);
  const [event, setEvent] = useState('MS');

  useEffect(() => {
    let changed = false;
    const params = new URLSearchParams(searchParams.toString());

    if (mode === 'historical' && model !== 'whr') {
      params.set('model', 'whr');
      params.set('mode', 'historical');
      changed = true;
    } else if (mode === 'seasonal' && model === 'whr') {
      params.set('model', 'elo');
      params.set('mode', 'seasonal');
      changed = true;
    }

    if (changed) {
      router.replace(`?${params.toString()}`);
    }
  }, [mode, model, searchParams, router]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [expandedPlayerId, setExpandedPlayerId] = useState<string | null>(null);
  const [playerHistories, setPlayerHistories] = useState<Record<string, HistoryPoint[]>>({});
  const [loadingHistories, setLoadingHistories] = useState<Record<string, boolean>>({});
  const [targetRank, setTargetRank] = useState<number | null>(null);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [selectedContinent, setSelectedContinent] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [continentOpen, setContinentOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [activeCountries, setActiveCountries] = useState<Record<string, number>>({});
  const [scrollMargin, setScrollMargin] = useState(0);
  const [inactivityThreshold, setInactivityThreshold] = useState(180);

  const throttledSetEvent = useThrottledCallback((ev: string) => {
    setEvent(ev);
    setLeaderboard([]);
    setOffset(0);
    setHasMore(true);
    setExpandedPlayerId(null);
  }, 200);

  const throttledSetMode = useThrottledCallback((targetMode: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('mode', targetMode);
    if (targetMode === 'historical') {
      params.set('model', 'whr');
    } else {
      params.set('model', 'elo');
    }
    router.push(`?${params.toString()}`);
    setLeaderboard([]);
    setOffset(0);
    setHasMore(true);
    setExpandedPlayerId(null);
  }, 200);

  const throttledJumpToRank = useThrottledCallback((rank: number) => {
    jumpToRank(rank);
  }, 200);

  const throttledTogglePlayerExpand = useThrottledCallback((player_id: string) => {
    if (expandedPlayerId === player_id) {
      setExpandedPlayerId(null);
    } else {
      setExpandedPlayerId(player_id);
      fetchPlayerHistory(player_id);
    }
  }, 200);

  const throttledSetContinent = useThrottledCallback((cont: string | null) => {
    setSelectedContinent(cont);
    setSelectedCountries([]);
    setLeaderboard([]);
    setOffset(0);
    setHasMore(true);
    setContinentOpen(false);
  }, 200);

  const throttledAddCountry = useThrottledCallback((code: string) => {
    if (selectedCountries.length < 5) {
      setSelectedCountries(prev => [...prev, code]);
      setLeaderboard([]);
      setOffset(0);
      setHasMore(true);
    }
  }, 200);

  const throttledRemoveCountry = useThrottledCallback((code: string) => {
    setSelectedCountries(prev => prev.filter(c => c !== code));
    setLeaderboard([]);
    setOffset(0);
    setHasMore(true);
  }, 200);
  
  const popoverRef = React.useRef<HTMLDivElement>(null);

  const expandedPlayer = useMemo(() => 
    leaderboard.find(p => p.player_id === expandedPlayerId),
    [leaderboard, expandedPlayerId]
  );

  const expandedPlayerHistory = useMemo(() => 
    expandedPlayerId ? (playerHistories[expandedPlayerId] || []) : [],
    [playerHistories, expandedPlayerId]
  );

  const expandedPlayerLoading = useMemo(() => 
    expandedPlayerId ? !!loadingHistories[expandedPlayerId] : false,
    [loadingHistories, expandedPlayerId]
  );

  const peakPoint = useMemo(() => {
    if (!expandedPlayer) return null;
    if (!expandedPlayerHistory || expandedPlayerHistory.length === 0) return { rating: expandedPlayer.rating, date: expandedPlayer.date };
    return expandedPlayerHistory.reduce((prev: HistoryPoint, current: HistoryPoint) => 
      (prev.rating > current.rating) ? prev : current, 
      expandedPlayerHistory[0]
    );
  }, [expandedPlayerHistory, expandedPlayer]);

  const chartData = useMemo(() => {
    if (!expandedPlayerHistory || expandedPlayerHistory.length === 0) return [];
    
    // Sort chronologically by date first to ensure calculations are correct
    const sorted = [...expandedPlayerHistory].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Find the peak rating point in the history
    let maxRating = -Infinity;
    let maxIdx = -1;
    for (let i = 0; i < sorted.length; i++) {
      if (sorted[i].rating > maxRating) {
        maxRating = sorted[i].rating;
        maxIdx = i;
      }
    }

    return sorted.map((h, index) => ({
      ...h,
      timestamp: new Date(h.date).getTime(),
      isPeak: index === maxIdx
    }));
  }, [expandedPlayerHistory]);

  const chartTicks = useMemo(() => {
    if (chartData.length === 0) return [];
    const minTime = chartData[0].timestamp;
    const maxTime = chartData[chartData.length - 1].timestamp;
    if (minTime === maxTime) {
      return [minTime];
    }
    return [
      minTime,
      minTime + (maxTime - minTime) * 0.3333333333333333,
      minTime + (maxTime - minTime) * 0.6666666666666666,
      maxTime
    ];
  }, [chartData]);

  const lastMatchDate = useMemo(() => {
    if (!expandedPlayer) return '';
    if (chartData.length > 0) {
      return chartData[chartData.length - 1].date;
    }
    return expandedPlayer.date || '';
  }, [chartData, expandedPlayer]);

  useEffect(() => {
    if (expandedPlayerId && popoverRef.current) {
      popoverRef.current.focus();
    }
  }, [expandedPlayerId]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/countries`)
      .then(res => res.json())
      .then(data => setActiveCountries(data))
      .catch(err => console.error("Failed to fetch countries:", err));
  }, []);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/inactivity-threshold?model=${model}`)
      .then(res => res.json())
      .then(data => {
        if (data && typeof data.inactivity_threshold === 'number') {
          setInactivityThreshold(data.inactivity_threshold);
        }
      })
      .catch(err => console.error("Failed to fetch inactivity threshold:", err));
  }, [model]);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 300) {
        setShowBackToTop(true);
      } else {
        setShowBackToTop(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
  const LIMIT = 25;

  const parentRef = React.useRef<HTMLDivElement>(null);

  const rowVirtualizer = useWindowVirtualizer({
    count: leaderboard.length,
    estimateSize: () => 56,
    overscan: 15,
    scrollMargin: scrollMargin,
  });

  useEffect(() => {
    if (parentRef.current) {
      setScrollMargin(parentRef.current.offsetTop);
    }
  }, [leaderboard.length]);


  const fetchData = useCallback((currentOffset: number, isInitial: boolean, customLimit?: number) => {
    const fetchLimit = customLimit || LIMIT;
    setTimeout(() => {
      if (isInitial) setLoading(true);
      else setLoadingMore(true);
    }, 0);

    const apiMode = mode === 'seasonal' ? 'current' : 'peak';

    let countryParam = '';
    if (selectedCountries.length > 0) {
      countryParam = `&country=${selectedCountries.join(',')}`;
    } else if (selectedContinent) {
      const countries = (continentMapping as Record<string, string[]>)[selectedContinent] || [];
      countryParam = `&country=${countries.join(',')}`;
    }

    fetch(`${API_BASE_URL}/api/leaderboard?event=${event}&model=${model}&mode=${apiMode}&period=3m&limit=${fetchLimit}&offset=${currentOffset}${countryParam}`)
      .then(res => res.json())
      .then(data => {
        const dataArray = Array.isArray(data) ? data : [];
        if (dataArray.length < fetchLimit) {
          setHasMore(false);
        }
        setLeaderboard(prev => isInitial ? dataArray : [...prev, ...dataArray]);
        setLoading(false);
        setLoadingMore(false);
      })
      .catch(err => {
        console.error("Failed to fetch leaderboard:", err);
        setLoading(false);
        setLoadingMore(false);
      });
  }, [event, model, mode, selectedCountries, selectedContinent]);

  const fetchPlayerHistory = useCallback((playerId: string) => {
    if (playerHistories[playerId]) return;

    setLoadingHistories(prev => ({ ...prev, [playerId]: true }));
    fetch(`${API_BASE_URL}/api/player/${playerId}/history?event=${event}&model=${model}`)
      .then(res => res.json())
      .then(data => {
        setPlayerHistories(prev => ({ ...prev, [playerId]: data }));
        setLoadingHistories(prev => ({ ...prev, [playerId]: false }));
      })
      .catch(err => {
        console.error("Failed to fetch player history:", err);
        setLoadingHistories(prev => ({ ...prev, [playerId]: false }));
      });
  }, [event, model, playerHistories]);

  const jumpToRank = async (rank: number) => {
    if (rank <= 0) return;

    setLoading(true);
    setLeaderboard([]);
    setHasMore(true);
    setTargetRank(rank);

    // Fetch in chunks of 1000 to show all cards above
    let currentOffset = 0;
    let allData: LeaderboardPlayer[] = [];
    
    try {
      const apiMode = mode === 'seasonal' ? 'current' : 'peak';
      let countryParam = '';
      if (selectedCountries.length > 0) {
        countryParam = `&country=${selectedCountries.join(',')}`;
      } else if (selectedContinent) {
        const countries = (continentMapping as Record<string, string[]>)[selectedContinent] || [];
        countryParam = `&country=${countries.join(',')}`;
      }

      while (currentOffset < rank) {
        const fetchLimit = Math.min(1000, rank - currentOffset);
        const url = `${API_BASE_URL}/api/leaderboard?event=${event}&model=${model}&mode=${apiMode}&period=3m&limit=${fetchLimit}&offset=${currentOffset}${countryParam}`;
        
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch");
        const data = await res.json();
        const dataArray = Array.isArray(data) ? data : [];
        
        allData = [...allData, ...dataArray];
        currentOffset += fetchLimit;
        
        if (dataArray.length < fetchLimit) {
          setHasMore(false);
          break; // No more data
        }
      }
      
      setLeaderboard(allData);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch leaderboard:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (targetRank !== null) {
      if (leaderboard.length >= targetRank) {
        rowVirtualizer.scrollToIndex(targetRank - 1, { align: 'start' });
        const timer = setTimeout(() => setTargetRank(null), 0);
        return () => clearTimeout(timer);
      } else if (!hasMore) {
        // Scroll to last item if target rank is out of bounds
        rowVirtualizer.scrollToIndex(leaderboard.length - 1, { align: 'start' });
        const timer = setTimeout(() => setTargetRank(null), 0);
        return () => clearTimeout(timer);
      }
    }
  }, [leaderboard, targetRank, hasMore, rowVirtualizer]);



  useEffect(() => {
    if (typeof window !== 'undefined') {
      if ('scrollRestoration' in window.history) {
        window.history.scrollRestoration = 'manual';
      }
      window.scrollTo(0, 0);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLeaderboard([]);
      setOffset(0);
      setHasMore(true);
      fetchData(0, true);
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchData]);

  useEffect(() => {
    if (offset > 0) {
      fetchData(offset, false);
    }
  }, [offset, fetchData]);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading && !loadingMore) {
        setOffset(prev => prev + LIMIT);
      }
    }, { threshold: 1.0 });


    const target = document.getElementById('infinite-scroll-trigger');
    if (target) observer.observe(target);

    return () => {
      if (target) observer.unobserve(target);
    };
  }, [hasMore, loading, loadingMore]);


  return (
    <div
      className="relative min-h-screen flex flex-col items-center justify-start space-y-8 py-8 overflow-x-clip bg-zinc-950 text-zinc-100"
      style={{
        backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 0)',
        backgroundSize: '36px 36px'
      }}
    >

      {/* Background Pattern */}
      <RetroGrid />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-4 text-center z-10 w-full max-w-7xl mx-auto px-4"
      >
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-zinc-100">
          World <span className="text-cyan-400">Leaderboard</span>
        </h1>
        <p className="text-sm text-zinc-400 max-w-2xl mx-auto">
          Real-time rankings based on advanced ELO and WHR rating systems.
        </p>
      </motion.div>

      {/* Controls Section */}
      <div className="w-full max-w-7xl mx-auto px-4 z-20 flex flex-wrap gap-4 items-center justify-between bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 backdrop-blur-sm">
        {/* Event Buttons */}
        <div className="flex gap-2">
          {["MS", "WS", "MD", "WD", "XD"].map((ev) => (
            <button
              key={ev}
              onClick={() => throttledSetEvent(ev)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${event === ev
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
                }`}
            >
              <motion.span
                className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
              />
              <span className="relative z-10">{ev}</span>
            </button>
          ))}
        </div>

        {/* Country and Continent Filters */}
        <div className="flex gap-4 items-center">
          {/* Continent Filter */}
          <div className="relative w-40">
            <button
              onClick={() => setContinentOpen(!continentOpen)}
              className="px-3 py-1.5 text-xs bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-md focus:outline-none focus:border-zinc-500 w-full text-left flex justify-between items-center"
            >
              <span>{selectedContinent || "All Continents"}</span>
              <svg 
                className={`w-3 h-3 fill-current transform transition-transform ${continentOpen ? 'rotate-180' : ''}`} 
                viewBox="0 0 20 20"
              >
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" fillRule="evenodd"></path>
              </svg>
            </button>
            <AnimatePresence>
              {continentOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="absolute z-50 top-full left-0 w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-md shadow-lg max-h-40 overflow-y-auto p-1"
                >
                  <div
                    className="p-1.5 text-xs text-zinc-100 hover:bg-zinc-800 rounded-md cursor-pointer"
                    onClick={() => throttledSetContinent(null)}
                  >
                    All Continents
                  </div>
                  {Object.keys(continentMapping).map((cont) => (
                    <div
                      key={cont}
                      className="p-1.5 text-xs text-zinc-100 hover:bg-zinc-800 rounded-md cursor-pointer"
                      onClick={() => throttledSetContinent(cont)}
                    >
                      {cont}
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Country Filter (Command Palette) */}
          <div className="relative w-80">
            <Command className="relative bg-zinc-900 border border-zinc-800 rounded-md">
              <div className="relative z-10 flex flex-wrap gap-2 items-center p-2 min-h-[40px]">
                <AnimatePresence>
                  {selectedCountries.map((code) => {
                    const name = Object.keys(countryCodes).find(key => (countryCodes as Record<string, string>)[key] === code) || code;
                    return (
                      <motion.span
                        key={code}
                        layout
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.8, opacity: 0 }}
                        className="flex items-center gap-1 bg-zinc-800 text-zinc-100 px-2 py-1 rounded-md text-xs border border-zinc-700"
                      >
                        <Flag code={code.toUpperCase()} size="S" />
                        <span>{name}</span>
                        <button
                          onClick={() => throttledRemoveCountry(code)}
                          className="ml-1 text-zinc-400 hover:text-zinc-100"
                        >
                          &times;
                        </button>
                      </motion.span>
                    );
                  })}
                </AnimatePresence>

                {selectedCountries.length < 5 && (
                  <Command.Input
                    placeholder="Search country..."
                    className="bg-transparent text-xs text-zinc-100 focus:outline-none flex-1 min-w-[100px]"
                    onFocus={() => setDropdownOpen(true)}
                    onBlur={() => setTimeout(() => setDropdownOpen(false), 200)}
                  />
                )}
              </div>

              {/* Breathing Glow Effect */}
              <motion.div
                className="absolute inset-0 rounded-md pointer-events-none border"
                animate={{
                  borderColor: [
                    "rgb(39, 39, 42)", // zinc-800
                    "rgb(63, 63, 70)", // zinc-700
                    "rgb(39, 39, 42)"
                  ],
                  boxShadow: [
                    "0 0 0px 0px rgba(24, 24, 27, 0)",
                    "0 0 4px 1px rgba(255, 255, 255, 0.03)",
                    "0 0 0px 0px rgba(24, 24, 27, 0)"
                  ]
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />

              {/* Dropdown List */}
              <AnimatePresence>
                {dropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="absolute z-50 top-full left-0 w-full mt-1"
                  >
                    <Command.List 
                      onMouseDown={(e) => e.preventDefault()} 
                      className="bg-zinc-900 border border-zinc-800 rounded-md shadow-lg max-h-40 overflow-y-auto p-1"
                    >
                  <Command.Empty className="text-xs text-zinc-500 p-2">No results found.</Command.Empty>
                   {Object.entries(countryCodes)
                    .reduce((acc, [name, code]) => {
                      if (!acc.find(item => item.code === code)) {
                        const count = activeCountries[name.toUpperCase()] || 0;
                        acc.push({ name, code, count });
                      }
                      return acc;
                    }, [] as { name: string, code: string, count: number }[])
                    .sort((a, b) => b.count - a.count)
                    .filter(({ code }) => {
                      if (selectedContinent) {
                        const allowedCountries = (continentMapping as Record<string, string[]>)[selectedContinent] || [];
                        return allowedCountries.includes(code.toUpperCase());
                      }
                      return true;
                    })
                    .filter(({ code }) => !selectedCountries.includes(code))
                    .map(({ name, code }) => (
                      <Command.Item
                        key={code}
                        onMouseDown={(e) => e.preventDefault()}
                        onSelect={() => throttledAddCountry(code)}
                        className="flex items-center gap-2 p-1.5 text-xs text-zinc-100 hover:bg-zinc-800 rounded-md cursor-pointer"
                      >
                        <Flag code={code.toUpperCase()} size="S" />
                        <span>{name}</span>
                      </Command.Item>
                    ))}
                    </Command.List>
                  </motion.div>
                )}
              </AnimatePresence>
            </Command>
          </div>
        </div>

        <div className="flex gap-4">
          {/* Mode Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => throttledSetMode('seasonal')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${mode === 'seasonal'
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
                }`}
            >
              <motion.span
                className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
              />
              <span className="relative z-10">Seasonal View</span>
            </button>
            <button
              onClick={() => throttledSetMode('historical')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all relative overflow-hidden group ${mode === 'historical'
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
                }`}
            >
              <motion.span
                className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
              />
              <span className="relative z-10">Greatest of all times</span>
            </button>
          </div>



          {/* Jump to Rank */}
          <div className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="Jump to rank"
              className="px-3 py-1.5 text-xs bg-zinc-950/40 text-zinc-100 border border-zinc-800/80 rounded-md focus:outline-none focus:border-zinc-500 w-32"
              maxLength={10}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  const val = (e.target as HTMLInputElement).value;
                  if (/^\d+$/.test(val)) {
                    throttledJumpToRank(parseInt(val));
                  }
                }
              }}
              onChange={(e) => {
                const val = e.target.value;
                if (val === '' || /^\d+$/.test(val)) {
                  // Keep it
                } else {
                  e.target.value = val.replace(/\D/g, '');
                }
              }}
            />
            <button
              onClick={() => {
                const input = document.querySelector('input[placeholder="Jump to rank"]') as HTMLInputElement;
                if (input && /^\d+$/.test(input.value)) {
                  throttledJumpToRank(parseInt(input.value));
                }
              }}
              className="px-3 py-1.5 text-xs font-semibold bg-zinc-950/40 text-zinc-400 border border-zinc-800/80 rounded-md hover:bg-zinc-800/80 hover:text-zinc-100 transition-all"
            >
              Go
            </button>
          </div>
        </div>
      </div>

      {/* Model Info & Note */}
      <div className="flex justify-between items-center w-full max-w-7xl mx-auto px-4 mb-6">
        {/* Model Name on Left */}
        <div className="text-[10px] text-zinc-600 uppercase font-mono font-bold">
          Model: {model.toUpperCase()}
        </div>

        {/* Note on Right */}
        <div className="text-[10px] text-zinc-600 font-mono text-right max-w-lg">
          {model === 'whr' ? (
            "the WHR uses global optimization; ratings may differ slightly from live Elo."
          ) : (
            "Elo tracks current form and immediate momentum; it is not calibrated for multi-era or historical comparisons."
          )}
        </div>
      </div>

      {/* Leaderboard Table Section */}
      <div className="w-full max-w-7xl mx-auto px-4 z-10">
        <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 rounded-lg">
          {loading ? (
            <div className="divide-y divide-zinc-800/60">
              <div className="grid grid-cols-12 gap-4 px-4 py-4 text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] border-b border-zinc-800/80 bg-zinc-900/80 backdrop-blur-md sticky top-0 z-50">
                <div className="col-span-1 text-center">Rank</div>
                <div className={`${hideForm ? (mode === 'seasonal' && model !== 'bwf' ? 'col-span-4' : 'col-span-5') : (mode === 'seasonal' && model !== 'bwf' ? 'col-span-3' : 'col-span-4')} pl-4`}>Player Profile</div>
                {mode === 'seasonal' && model !== 'bwf' && <div className="col-span-1 text-center">BWF Rank</div>}
                <div className="col-span-2 text-center">{model === 'bwf' ? 'Points' : 'Rating'}</div>
                <div className="col-span-2 text-center">{mode === 'seasonal' ? 'Trend (3M)' : 'Win Rate'}</div>
                {!hideForm && <div className="col-span-1 text-center">{mode === 'seasonal' ? 'Form (3M)' : 'Peak Global Rank'}</div>}
                <div className="col-span-2 text-center">{mode === 'seasonal' ? 'Last Played' : 'Date Achieved'}</div>
              </div>
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="grid grid-cols-12 gap-4 items-center px-4 py-4 border-b border-zinc-800/40 animate-pulse">
                  <div className="col-span-1 flex items-center justify-center">
                    <div className="h-5 w-4 bg-zinc-800/60 rounded" />
                  </div>
                  <div className={`${hideForm ? (mode === 'seasonal' && model !== 'bwf' ? 'col-span-4' : 'col-span-5') : (mode === 'seasonal' && model !== 'bwf' ? 'col-span-3' : 'col-span-4')} flex items-center gap-4`}>
                    <div className="w-8 h-6 bg-zinc-800/60 rounded-sm" />
                    <div className="space-y-1.5 flex-1">
                      <div className="h-4 bg-zinc-800/60 rounded w-2/3" />
                      <div className="h-3 bg-zinc-800/40 rounded w-1/3" />
                    </div>
                  </div>
                  {mode === 'seasonal' && model !== 'bwf' && (
                    <div className="col-span-1 flex justify-center">
                      <div className="h-5 w-8 bg-zinc-800/60 rounded" />
                    </div>
                  )}
                  <div className="col-span-2 flex justify-center">
                    <div className="h-6 w-12 bg-zinc-800/60 rounded" />
                  </div>
                  <div className="col-span-2 flex justify-center">
                    <div className="h-5 w-10 bg-zinc-800/60 rounded" />
                  </div>
                  {!hideForm && (
                    <div className="col-span-1 flex justify-center">
                      <div className="h-5 w-12 bg-zinc-800/60 rounded" />
                    </div>
                  )}
                  <div className="col-span-2 flex justify-center">
                    <div className="h-4 w-16 bg-zinc-800/60 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="p-12 text-center text-zinc-400 font-mono text-xs uppercase tracking-widest">No player info</div>
          ) : (
            <div>
              <div className="grid grid-cols-12 gap-4 px-4 py-4 text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] border-b border-zinc-800/80 bg-zinc-900/80 backdrop-blur-md sticky top-0 z-50">
                <div className="col-span-1 text-center">Rank</div>
                <div className={`${hideForm ? (mode === 'seasonal' && model !== 'bwf' ? 'col-span-4' : 'col-span-5') : (mode === 'seasonal' && model !== 'bwf' ? 'col-span-3' : 'col-span-4')} pl-4`}>Player Profile</div>
                {mode === 'seasonal' && model !== 'bwf' && <div className="col-span-1 text-center">BWF Rank</div>}
                <div className="col-span-2 text-center">{model === 'bwf' ? 'Points' : 'Rating'}</div>
                <div className="col-span-2 text-center">{mode === 'seasonal' ? 'Trend (3M)' : 'Win Rate'}</div>
                {!hideForm && <div className="col-span-1 text-center">{mode === 'seasonal' ? 'Form (3M)' : 'Peak Global Rank'}</div>}
                <div className="col-span-2 text-center">{mode === 'seasonal' ? 'Last Played' : 'Date Achieved'}</div>
              </div>

              <div ref={parentRef}>

                <div
                  style={{
                    height: `${rowVirtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                  }}
                >
                  {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                    const player = leaderboard[virtualRow.index];
                    return (
                      <PlayerCard
                        key={player.player_id}
                        player={player}
                        index={virtualRow.index}
                        virtualRow={virtualRow}
                        isExpanded={expandedPlayerId === player.player_id}
                        hideForm={hideForm}
                        mode={mode}
                        onToggleExpand={throttledTogglePlayerExpand}
                        measureElement={rowVirtualizer.measureElement}
                        scrollMargin={scrollMargin}
                      />
                    );
                  })}
                </div>
              </div>

              {hasMore && (
                <div id="infinite-scroll-trigger" className="h-10 flex items-center justify-center text-zinc-500 font-mono text-xs uppercase tracking-widest">
                  {loadingMore ? "Loading more..." : ""}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
          {showBackToTop && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="fixed bottom-8 right-8 z-50 w-10 h-10 bg-zinc-800 text-zinc-500 rounded-full flex items-center justify-center border border-zinc-700 hover:bg-zinc-700 transition-all shadow-lg"
              title="Back to Top"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5"></line>
                <polyline points="5 12 12 5 19 12"></polyline>
              </svg>
            </motion.button>
          )}
        </AnimatePresence>

        {/* Global Analytics Popover */}
        {mounted && createPortal(
          <AnimatePresence>
            {expandedPlayerId && expandedPlayer && (
              <>
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[9998] cursor-pointer"
                  onClick={() => setExpandedPlayerId(null)}
                />
                
                <motion.div
                  ref={popoverRef}
                  tabIndex={-1}
                  initial={{ opacity: 0, scale: 0.98, x: '-50%', y: '-48%' }}
                  animate={{ opacity: 1, scale: 1, x: '-50%', y: '-50%' }}
                  exit={{ opacity: 0, scale: 0.98, x: '-50%', y: '-48%' }}
                  className="fixed left-1/2 top-1/2 w-[92vw] h-auto max-h-[90vh] md:max-h-[85vh] max-w-[1100px] bg-zinc-950/80 backdrop-blur-md border border-zinc-800/80 rounded-2xl p-6 md:p-10 shadow-[0_64px_256px_-24px_rgba(0,0,0,1)] z-[9999] overflow-y-auto outline-none scrollbar-thin scrollbar-thumb-zinc-850"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-2xl">
                    <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_0%,rgba(56,189,248,0.05),transparent_60%)]" />
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.02] brightness-200" />
                  </div>

                  <div className="flex justify-between items-start mb-8">
                    <div className="flex-1">
                      <div className="mb-4">
                        <Link 
                          href={`/player/${expandedPlayer.player_id}`} 
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white rounded-md text-xs font-semibold tracking-wide uppercase transition-all duration-300 hover:scale-[1.02] hover:border-zinc-700 active:scale-[0.98]"
                        >
                          <svg className="w-3.5 h-3.5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                          <span>View Profile</span>
                        </Link>
                      </div>
                      <div className="flex flex-col md:flex-row md:items-center gap-6">
                        <div className="flex items-center gap-4">
                          {getCountryCode(expandedPlayer.country) && (
                            <div className="w-12 h-8 rounded-md overflow-hidden flex items-center justify-center bg-zinc-900 border border-zinc-800">
                              <Flag code={getCountryCode(expandedPlayer.country)!} className="w-full h-full" />
                            </div>
                          )}
                          <div>
                            <Link href={`/player/${expandedPlayer.player_id}`} onClick={(e) => e.stopPropagation()}>
                              <h3 className="text-3xl md:text-4xl font-bold text-white tracking-tight hover:text-sky-400 transition-colors cursor-pointer">{expandedPlayer.name}</h3>
                            </Link>
                            <div className="text-xs text-zinc-500 font-mono uppercase tracking-widest mt-1">{expandedPlayer.country}</div>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-8 md:ml-12 md:pl-12 md:border-l md:border-zinc-800/50">
                          <div>
                            <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">{model === 'bwf' ? 'Peak Points' : 'Peak Rating'}</div>
                            <div className="text-xl font-bold text-sky-400 font-mono">
                              {Math.round((peakPoint?.rating || 0) + (model === 'whr' ? 1000 : 0))}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">Win Rate</div>
                            <div className="text-xl font-bold text-zinc-100 font-mono">
                              {expandedPlayer.winrate ? `${expandedPlayer.winrate}%` : '--'}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">Status</div>
                            {(() => {
                              const lastPlayed = expandedPlayer.date;
                              if (!lastPlayed) {
                                return (
                                  <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-zinc-600" />
                                    <span className="text-xl font-bold text-zinc-500 font-mono">Unknown</span>
                                  </div>
                                );
                              }
                              const daysSince = Math.floor(
                                (new Date().getTime() - new Date(lastPlayed).getTime()) / (1000 * 60 * 60 * 24)
                              );
                              const isActive = daysSince <= inactivityThreshold;
                              return (
                                <div className="flex items-center gap-2">
                                  <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-500'}`} />
                                  <span className={`text-xl font-bold font-mono ${isActive ? 'text-emerald-500' : 'text-zinc-500'}`}>
                                    {isActive ? 'Active' : 'Inactive'}
                                  </span>
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                    </div>
                    <button 
                      onClick={() => setExpandedPlayerId(null)}
                      className="p-2 hover:bg-zinc-800/50 rounded-lg text-zinc-500 hover:text-white transition-all border border-zinc-800/50"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>

                  <div className="h-[30vh] md:h-[35vh] min-h-[250px] w-full relative mb-8 rounded-xl overflow-hidden bg-zinc-950/50 border border-zinc-800/50 p-4">
                    {expandedPlayerLoading ? (
                      <div className="h-full flex flex-col items-center justify-center gap-8">
                        <div className="w-48 h-2 bg-zinc-900 overflow-hidden rounded-full relative">
                          <motion.div 
                            className="absolute inset-0 bg-sky-500 shadow-[0_0_30px_#0ea5e9]"
                            animate={{ left: ["-100%", "100%"] }}
                            transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
                          />
                        </div>
                        <span className="text-[11px] text-zinc-600 uppercase tracking-widest font-bold animate-pulse">Syncing Player History...</span>
                      </div>
                    ) : chartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart 
                          data={chartData}
                          margin={{ top: 20, right: 20, left: 0, bottom: 20 }}
                        >
                          <defs>
                            <linearGradient id="popoverGlow" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2} />
                              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="#18181b" vertical={false} strokeDasharray="3 3" />
                          <XAxis 
                            dataKey="timestamp" 
                            type="number" 
                            domain={['dataMin', 'dataMax']} 
                            ticks={chartTicks}
                            tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'monospace' }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                            dy={10}
                          />
                          <YAxis 
                            domain={['dataMin - 50', 'dataMax + 50']} 
                            tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'monospace' }}
                            axisLine={false}
                            tickLine={false}
                            dx={-10}
                          />
                          <RechartsTooltip
                            contentStyle={{ backgroundColor: '#09090b', border: '1px solid #27272a', borderRadius: '8px', padding: '12px', boxShadow: '0 20px 40px rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
                            itemStyle={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '18px', fontFamily: 'monospace' }}
                            labelStyle={{ color: '#52525b', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}
                            labelFormatter={(label) => new Date(label).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            formatter={(value: number) => [Math.round(value + (model === 'whr' ? 1000 : 0)), model === 'bwf' ? "Points" : "Rating"]}
                          />
                          <Area
                            type="monotone"
                            dataKey="rating"
                            stroke="#38bdf8"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#popoverGlow)"
                            animationDuration={1500}
                            dot={(props: any) => {
                              const { cx, cy, payload } = props;
                              if (payload?.isPeak) {
                                return (
                                  <g key={`peak-dot-${payload.timestamp}`}>
                                    <circle 
                                      cx={cx} 
                                      cy={cy} 
                                      r={10} 
                                      fill="#38bdf8" 
                                      className="animate-ping" 
                                      style={{ transformOrigin: `${cx}px ${cy}px` }}
                                      opacity={0.4} 
                                    />
                                    <circle 
                                      cx={cx} 
                                      cy={cy} 
                                      r={4.5} 
                                      fill="#38bdf8" 
                                      stroke="#09090b" 
                                      strokeWidth={1.5} 
                                    />
                                  </g>
                                );
                              }
                              return <g key={`dot-empty-${props.index}`} />;
                            }}
                            activeDot={{
                              r: 5,
                              fill: '#38bdf8',
                              stroke: '#09090b',
                              strokeWidth: 1.5
                            }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-zinc-800 font-bold text-sm uppercase tracking-widest">No History Found</div>
                    )}
                  </div>

                  <div className="flex flex-col md:flex-row justify-between items-center gap-4 border-t border-zinc-900 pt-6">
                    <div className="text-xs text-zinc-600 font-mono">
                      Global Analytics Stream // Model: {model.toUpperCase()}
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">
                        {mode === 'peak' ? 'Peak Rating Date' : 'Last Match Date'}
                      </div>
                      <div className="text-xl font-bold font-mono text-zinc-400">
                        {mode === 'peak' ? (peakPoint?.date || expandedPlayer.date) : lastMatchDate}
                      </div>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>,
          document.body
        )}
    </div>
  );
}

export default function LeaderboardPage() {
  return (
    <React.Suspense fallback={
      <div className="relative min-h-screen flex flex-col items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="text-zinc-400 font-mono text-xs uppercase tracking-widest animate-pulse">
          Loading Leaderboard...
        </div>
      </div>
    }>
      <LeaderboardContent />
    </React.Suspense>
  );
}

