'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, Transition } from 'framer-motion';
import { BorderBeam } from '@/components/magicui/border-beam';
import { Flag } from '@/components/ui/flag';
import { NumberTicker } from '@/components/magicui/number-ticker';
import { API_BASE_URL } from '@/lib/api';
import { getCountryCode, formatEliteName, LightningStrike } from './utils';

interface DisciplineTheme {
  bg: string;
  accent: string;
  textGradient: string;
  beamColor: string;
  beamColorFrom?: string;
  beamDuration: number;
  texture?: string;
  textureSize?: string;
  textureOpacity?: number;
  motion: Transition;
  font: string;
  label: string;
  secondaryLabel?: string;
}

const DISCIPLINE_THEMES: Record<string, DisciplineTheme> = {
  MS: {
    bg: "bg-[#001f3f]",
    accent: "text-[#FFD700]",
    textGradient: "from-yellow-400 via-amber-200 to-yellow-500",
    beamColor: "#00ffff", 
    beamColorFrom: "#FFD700",
    beamDuration: 4,
    texture: "repeating-linear-gradient(45deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 4px, transparent 4px, transparent 12px)",
    motion: { type: "spring", stiffness: 300, damping: 15 },
    font: "font-black tracking-tighter",
    label: "Power & Dominance"
  },
  WS: {
    bg: "bg-[#1a1a1a]",
    accent: "text-pink-500",
    textGradient: "from-pink-400 via-rose-200 to-pink-500",
    beamColor: "#ec4899",
    beamDuration: 6,
    texture: "radial-gradient(circle, rgba(236,72,153,0.05) 1px, transparent 1px)",
    textureSize: "20px 20px",
    motion: { ease: "easeInOut", duration: 0.8 },
    font: "font-bold tracking-tight",
    label: "ETHEREAL BLOOM"
  },
  MD: {
    bg: "bg-[#111111]",
    accent: "text-[#ff0033]",
    textGradient: "from-red-500 via-rose-300 to-red-600",
    beamColor: "#ff0033",
    beamColorFrom: "#2a0202",
    beamDuration: 1.5,
    texture: "url(\"data:image/svg+xml,%3Csvg width='24' height='42' viewBox='0 0 24 42' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M12 0l12 6.928v13.856L12 27.712 0 20.784V6.928L12 0zm0 41.568l12-6.928v-13.856l-12-6.928-12 6.928v13.856l12 6.928z' fill='%23ffffff' fill-opacity='0.03' fill-rule='evenodd'/%3E%3C/svg%3E\")",
    motion: { type: "spring", stiffness: 500, damping: 20 },
    font: "font-black uppercase tracking-normal", 
    label: "EXTREME VELOCITY",
    secondaryLabel: "FRICTION & SPEED"
  },
  WD: {
    bg: "bg-[#161640]",
    accent: "text-[#d4af37]",
    textGradient: "from-amber-300 via-yellow-200 to-yellow-500",
    beamColor: "#d4af37", 
    beamColorFrom: "#161640",
    beamDuration: 8,
    texture: "url(\"data:image/svg+xml,%3Csvg width='20' height='34.64' viewBox='0 0 20 34.64' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M10 0L20 5.77V17.32L10 23.09L0 17.32V5.77L10 0z' fill='none' stroke='%23ffffff' stroke-opacity='0.12' stroke-width='0.5'/%3E%3C/svg%3E\")",
    textureSize: "20px 34.64px",
    motion: { duration: 1.2, ease: [0.22, 1, 0.36, 1] },
    font: "font-bold tracking-[0.1em]", 
    label: "THE IRON WALL",
    secondaryLabel: "DEFENSIVE EFFICIENCY"
  },
  XD: {
    bg: "bg-[#161640]",
    accent: "text-purple-400", 
    textGradient: "from-cyan-400 via-purple-300 to-indigo-400",
    beamColor: "#06b6d4",
    beamColorFrom: "#ef4444",
    beamDuration: 5,
    texture: "noise",
    textureOpacity: 0.07,
    motion: { duration: 0.8, ease: "circOut" },
    font: "font-black tracking-normal",
    label: "TOTAL CONVERGENCE",
    secondaryLabel: "DYNAMIC EQUILIBRIUM"
  }
};

interface SynergyPartner {
  player_id: string;
  name: string;
  score: number;
}

interface PreviewPlayer {
  player_id: string;
  name: string;
  country: string;
  rating: number;
  date: string;
  synergy_partner?: SynergyPartner;
}

// A pure pseudo-random number generator to satisfy React Compiler purity rules
function pseudoRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export function LeaderboardPreviewCard() {
  const [data, setData] = useState<Record<string, PreviewPlayer> | null>(null);
  const [activeEvent, setActiveEvent] = useState('MS');
  const [activeModel, setActiveModel] = useState('elo');
  const events = ["MS", "WS", "MD", "WD", "XD"];
  const theme = DISCIPLINE_THEMES[activeEvent];

  const wsParticles = React.useMemo(() => {
    return Array.from({ length: 20 }, (_, i) => ({
      id: i,
      x: pseudoRandom(i + 1) * 800,
      duration: pseudoRandom(i + 2) * 5 + 5,
      delay: pseudoRandom(i + 3) * 5,
    }));
  }, []);

  const xdParticles = React.useMemo(() => {
    return Array.from({ length: 14 }, (_, i) => ({
      id: i,
      initialRotation: (i / 14) * 360,
      delay: pseudoRandom(i + 4) * 12,
      duration: pseudoRandom(i + 5) * 6 + 14,
      size: pseudoRandom(i + 6) * 4 + 4,
    }));
  }, []);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/dashboard/leaderboard-preview?model=${activeModel}`)
      .then(res => res.json())
      .then(resData => {
        if (active) setData(resData);
      })
      .catch(console.error);
    return () => {
      active = false;
    };
  }, [activeModel]);

  const player = data?.[activeEvent];
  const isDoubles = ['MD', 'WD', 'XD'].includes(activeEvent);

  const containerVariants = {
    initial: { opacity: 0, scale: 0.9, filter: 'blur(10px)' },
    enter: { 
      opacity: 1, scale: 1, filter: 'blur(0px)',
      transition: { duration: 0.5, staggerChildren: 0.1, when: "beforeChildren" } 
    },
    exit: { opacity: 0, scale: 1.1, filter: 'blur(20px)', transition: { duration: 0.3 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 30, filter: 'blur(8px)' },
    enter: { opacity: 1, y: 0, filter: 'blur(0px)', transition: theme.motion }
  };

  return (
    <div 
      className={`h-[480px] relative flex flex-col p-6 overflow-hidden transition-all duration-700 rounded-2xl border border-zinc-700/50 brightness-110 ${theme.bg}`}
    >
      {/* Entry gleaming effect sweeps across the whole card */}
      <motion.div
        key={`gleam-${activeEvent}`}
        initial={{ x: "-150%", skewX: -25, opacity: 0.6 }}
        animate={{ x: "250%", opacity: 0 }}
        transition={{ duration: 1.4, ease: [0.25, 0.1, 0.25, 1] }}
        className="absolute inset-0 pointer-events-none z-30 bg-gradient-to-r from-transparent via-white/15 to-transparent w-[60%]"
      />

      <BorderBeam size={400} duration={theme.beamDuration} colorFrom={theme.beamColorFrom || theme.beamColor} colorTo={theme.beamColor} borderWidth={1.5} className="absolute inset-0 pointer-events-none z-20" />

      <div className="flex items-center justify-between mb-6 relative z-30">
        <div className="space-y-1.5">
          <h3 className="text-2xl font-black italic tracking-tighter uppercase transition-colors duration-700 py-1 px-2 leading-normal bg-gradient-to-b from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent drop-shadow-md">WORLD ELITE</h3>
          <div className="flex bg-black/30 p-0.5 rounded-lg border border-white/5 backdrop-blur-sm w-fit ml-2">
            {["elo", "whr", "bwf"].map(m => (
              <button 
                key={m} 
                onClick={() => {
                  setData(null);
                  setActiveModel(m);
                }} 
                className={`px-2 py-0.5 text-[8px] font-black rounded-md transition-all uppercase ${activeModel === m ? 'bg-zinc-100 text-black shadow-sm font-bold' : 'text-zinc-500 hover:text-white'}`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex bg-black/40 p-1 rounded-xl border border-white/5 backdrop-blur-md">
           {events.map(ev => (
             <button key={ev} onClick={() => setActiveEvent(ev)} className={`px-3 py-1.5 text-[10px] font-black rounded-lg transition-all ${activeEvent === ev ? 'bg-zinc-100 text-black shadow-lg' : 'text-zinc-500 hover:text-white'}`}>{ev}</button>
           ))}
        </div>
      </div>

      <AnimatePresence mode="popLayout" initial={false}>
        {!player ? (
           <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-grow flex items-center justify-center text-zinc-600 text-xs italic font-mono uppercase tracking-widest relative z-30">ENGAGING ANALYTICS ENGINE...</motion.div>
        ) : (
          <motion.div 
            key={activeEvent} 
            variants={containerVariants} 
            initial="initial" 
            animate="enter" 
            exit="exit" 
            className="flex-none h-[360px] flex flex-col relative z-20 rounded-2xl mx-4 mt-2 mb-10 overflow-hidden border border-white/5 shadow-inner"
            style={{
              backgroundColor: 'rgba(0, 0, 0, 0.45)',
              backdropFilter: 'blur(6px)',
              backgroundImage: theme.texture && theme.texture !== 'noise' ? theme.texture : undefined,
              backgroundSize: theme.textureSize || 'auto',
              backgroundClip: 'padding-box',
            }}
          >
            {/* Visual Effects Sub-layers */}
            {theme.texture === 'noise' && (
              <div 
                className="absolute inset-0 pointer-events-none z-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='${theme.textureOpacity ?? 0.04}'/%3E%3C/svg%3E")`,
                  backgroundClip: 'padding-box',
                }}
              />
            )}

            {activeEvent === 'MS' && (
              <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
                <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {[...Array(2)].map((_, i) => <LightningStrike key={i} id={i} />)}
                </svg>
              </div>
            )}

            {activeEvent === 'WS' && (
              <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
                {wsParticles.map((p) => (
                  <motion.div
                    key={p.id}
                    initial={{ x: p.x, y: -20, opacity: 0 }}
                    animate={{ y: 500, opacity: [0, 0.4, 0] }}
                    transition={{ duration: p.duration, repeat: Infinity, ease: "linear", delay: p.delay }}
                    className="absolute w-1 h-1 bg-pink-300/40 rounded-full blur-[1px]"
                  />
                ))}
              </div>
            )}

            {activeEvent === 'WD' && (
              <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
                {/* Majestic, highly authentic medieval shield watermark in center */}
                <div className="absolute inset-0 flex items-center justify-center opacity-[0.035]">
                  <svg className="w-[280px] h-[280px] text-[#d4af37]" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M20,15 C20,15 50,8 80,15 C80,35 78,65 50,92 C22,65 20,35 20,15 Z" fillRule="evenodd" />
                    <line x1="50" y1="8" x2="50" y2="92" />
                    <path d="M30,22 C30,22 50,16 70,22 C70,38 68,58 50,80 C32,58 30,38 30,22 Z" strokeWidth="1.2" />
                  </svg>
                </div>
                {/* High-tech digital laser scanner with trailing gradient and zero gap */}
                <motion.div
                  initial={{ y: -60 }}
                  animate={{ y: 360 }}
                  transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
                  className="absolute left-0 right-0 h-[57px] pointer-events-none z-30 flex flex-col justify-end"
                >
                  <div className="h-[56px] w-full bg-gradient-to-t from-[#d4af37]/18 via-[#d4af37]/4 to-transparent" />
                  <div className="h-[1px] w-full bg-[#d4af37] shadow-[0_0_12px_#d4af37]" />
                </motion.div>
              </div>
            )}

            {activeEvent === 'MD' && (
              <div className="absolute inset-0 flex items-center justify-center overflow-hidden bg-transparent pointer-events-none z-10">
                {/* 
                  FLICKER WRAPPER: 
                  Controls the sudden disappearance/reappearance of the entire graphic 
                */}
                <motion.div
                  className="relative w-[500px] h-[500px] flex items-center justify-center"
                  animate={{
                    opacity: [1, 1, 0, 1, 0, 0, 1, 0, 1, 1],
                  }}
                  transition={{
                    duration: 5, // Loops every 5 seconds
                    repeat: Infinity,
                    ease: "linear",
                    // Stays perfectly solid for 96% of the cycle, then executes ultra-rapid cuts at the tail end
                    times: [0, 0.96, 0.965, 0.97, 0.975, 0.98, 0.985, 0.99, 0.995, 1],
                  }}
                >
                  {/* BACKGROUND GHOST 1: Furthest Left, sharp, highly transparent */}
                  <XIcon className="absolute -translate-x-5 translate-y-1 scale-95" style={{ color: 'rgba(220, 38, 38, 0.03)' }} strokeWidth={2.5} />

                  {/* BACKGROUND GHOST 2: Left, sharp, slightly skewed */}
                  <XIcon className="absolute -translate-x-2 translate-y-0.5 scale-98 skew-x-2" style={{ color: 'rgba(220, 38, 38, 0.05)' }} strokeWidth={3} />

                  {/* BACKGROUND GHOST 3: Center Left, sharp */}
                  <XIcon className="absolute translate-x-1 -translate-y-0.5 scale-101" style={{ color: 'rgba(239, 68, 68, 0.07)' }} strokeWidth={3.5} />

                  {/* BACKGROUND GHOST 4: Right, skewed tracking ghost */}
                  <XIcon className="absolute translate-x-3 translate-y-0.5 scale-103 skew-x-3" style={{ color: 'rgba(239, 68, 68, 0.06)' }} strokeWidth={4} />

                  {/* BACKGROUND GHOST 5: Furthest Right, sharp */}
                  <XIcon className="absolute translate-x-5 -translate-y-1 scale-105 -skew-x-3" style={{ color: 'rgba(220, 38, 38, 0.04)' }} strokeWidth={3} />

                  {/* MAIN X: Sharp, tucked into the background, even thicker */}
                  <XIcon className="relative" style={{ color: 'rgba(220, 38, 38, 0.12)' }} strokeWidth={5.5} />

                  {/* FAINT WHITE SPEED LINES: Intersecting the X sharply */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <div className="absolute h-[1.5px] w-[120%] bg-white/40 rotate-[15deg] blur-[0.5px]" />
                    <div className="absolute h-[1px] w-[110%] bg-white/30 rotate-[-10deg] blur-[0.5px]" />
                  </div>
                </motion.div>
              </div>
            )}

            {activeEvent === 'XD' && (
              <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden">
                {/* Simplified Yin Yang converging pieces - Absolute position overlap for PERFECT touch in center */}
                <div className="absolute inset-0 flex items-center justify-center opacity-[0.11]">
                  {/* Left Blue piece */}
                  <motion.div
                    initial={{ x: -280, opacity: 0, rotate: -270 }}
                    animate={{ x: 0, opacity: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 12, damping: 10, delay: 0.2 }}
                    className="absolute w-[390px] h-[390px] text-cyan-500 blur-[10px]"
                  >
                    <svg className="w-full h-full" viewBox="0 0 100 100" fill="currentColor">
                      <path d="M50,0 A50,50 0 0,0 50,100 A25,25 0 0,0 50,50 A25,25 0 0,1 50,0 Z" />
                    </svg>
                  </motion.div>

                  {/* Right Red piece */}
                  <motion.div
                    initial={{ x: 280, opacity: 0, rotate: 270 }}
                    animate={{ x: 0, opacity: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 12, damping: 10, delay: 0.2 }}
                    className="absolute w-[390px] h-[390px] text-red-500 blur-[10px]"
                  >
                    <svg className="w-full h-full" viewBox="0 0 100 100" fill="currentColor">
                      <path d="M50,100 A50,50 0 0,0 50,0 A25,25 0 0,0 50,50 A25,25 0 0,1 50,100 Z" />
                    </svg>
                  </motion.div>
                </div>

                {/* Smooth, gradual Archimedean spiral-gravitating particles - Even slower and less rotation */}
                <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                  <div className="relative w-0 h-0">
                    {xdParticles.map((p) => {
                      return (
                        <div 
                          key={p.id} 
                          className="absolute"
                          style={{
                            width: 0,
                            height: 0,
                            transform: `rotate(${p.initialRotation}deg)`,
                          }}
                        >
                          <motion.div
                            animate={{ rotate: 270 }} // Less rotation: 270 degrees instead of 720 degrees!
                            transition={{
                              duration: p.duration,
                              repeat: Infinity,
                              ease: "linear",
                              delay: p.delay,
                            }}
                            className="absolute origin-center"
                          >
                            <motion.div
                              initial={{ x: 220, opacity: 0, scale: 1.2 }}
                              animate={{ 
                                x: 0, 
                                opacity: [0, 0.6, 0.45, 0.1, 0],
                                scale: [1.2, 0.8, 0.5, 0.2, 0]
                              }}
                              transition={{
                                duration: p.duration,
                                repeat: Infinity,
                                ease: "easeIn",
                                delay: p.delay,
                              }}
                              className={`absolute -translate-y-1/2 rounded-full blur-[1px] ${
                                p.id % 2 === 0 
                                  ? 'bg-cyan-500 shadow-[0_0_8px_#06b6d4]' 
                                  : 'bg-red-500 shadow-[0_0_8px_#ef4444]'
                              }`}
                              style={{
                                width: p.size,
                                height: p.size,
                              }}
                            />
                          </motion.div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            <div className="flex-grow grid grid-cols-2 items-end relative z-20 px-10 pb-6 pt-4 h-full">
              <div className="space-y-6 pb-2">
                 <motion.div variants={itemVariants} className="absolute top-6 left-10 w-20 h-14 drop-shadow-xl z-50">
                    <Flag code={getCountryCode(player.country) || 'un'} width="w320" className="w-full h-full object-contain rounded-sm" />
                 </motion.div>
                 
                 <div className="space-y-4 relative">
                    <motion.div variants={itemVariants} className={`${formatEliteName(player.name, isDoubles).typography} drop-shadow-[0_4px_12px_rgba(0,0,0,0.5)]`}>
                        {(() => {
                          const formatted = formatEliteName(player.name, isDoubles);
                          const isMD = activeEvent === 'MD';
                          return (
                            <>
                              {formatted.lines.map((line, i) => {
                                const gradientClass = activeEvent === 'XD' 
                                  ? 'from-red-500 via-rose-400 to-red-600' 
                                  : theme.textGradient;
                                return (
                                  <motion.div 
                                    key={i} 
                                    className={`leading-none bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}
                                    animate={isMD ? { opacity: [1, 1, 0.15, 0.9, 0.05, 1, 1] } : {}}
                                    transition={isMD ? { repeat: Infinity, duration: 15, times: [0, 0.94, 0.95, 0.96, 0.97, 0.98, 1], ease: "linear" as const, delay: 0.5 } : {}}
                                  >
                                    {line}
                                  </motion.div>
                                );
                              })}
                              {player.synergy_partner && (
                                <div className="mt-4 opacity-90">
                                  {formatEliteName(player.synergy_partner.name, true).lines.map((line, i) => {
                                    const gradientClass = activeEvent === 'XD' 
                                      ? 'from-cyan-400 via-blue-300 to-indigo-400' 
                                      : theme.textGradient;
                                    return (
                                      <motion.div 
                                        key={i} 
                                        className={`leading-none bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}
                                        animate={isMD ? { opacity: [1, 1, 0.1, 0.8, 0.05, 1, 1] } : {}}
                                        transition={isMD ? { repeat: Infinity, duration: 15, times: [0, 0.93, 0.94, 0.95, 0.96, 0.97, 1], ease: "linear" as const, delay: 2.1 } : {}}
                                      >
                                        {line}
                                      </motion.div>
                                    );
                                  })}
                                </div>
                              )}
                            </>
                          );
                        })()}
                    </motion.div>
                 </div>
              </div>

              <div className="flex flex-col items-end justify-end h-full pb-6">
                <motion.div variants={itemVariants} className="text-right flex flex-col items-end translate-x-4">
                  <div className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest bg-white/5 border border-white/10 text-zinc-300 mb-2 backdrop-blur-md shadow-lg flex items-center gap-1.5 leading-normal">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee] animate-pulse" />
                    {activeModel === 'bwf' ? 'WORLD BWF POINTS' : 'WORLD RATING'}
                  </div>
                  <div className="text-[140px] font-black tracking-[-0.06em] leading-[0.7] relative text-white drop-shadow-[0_30px_60px_rgba(0,0,0,0.8)]">
                    <NumberTicker value={Math.round(player.rating)} />
                  </div>
                </motion.div>
              </div>
            </div>
            <div className="absolute inset-0 pointer-events-none z-40 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.7)_120%)] rounded-2xl" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Crisp, scaleable SVG implementation of the aggressive "X"
function XIcon({ className, style, strokeWidth = 10 }: { className?: string; style?: React.CSSProperties; strokeWidth?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      className={className}
      style={style}
    >
      <path
        strokeLinecap="square"
        strokeLinejoin="miter"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}
