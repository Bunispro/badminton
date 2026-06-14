'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { BorderBeam } from "@/components/magicui/border-beam";
import { NameShine } from '@/components/ui/name-shine';
import { getBeamColors } from '../utils';

interface PlayerHeaderProps {
  player?: {
    name?: string;
    country?: string;
    disciplines?: string[];
  } | null;
  stats?: {
    current_rank?: number;
    inactivity_threshold?: number;
  } | null;
  countryCode?: string | null;
  daysSinceLastMatch?: number | null;
  loading?: boolean;
}

export const PlayerHeader = ({ player, stats, countryCode, daysSinceLastMatch, loading }: PlayerHeaderProps) => {
  const colors = getBeamColors(countryCode || "");
  const threshold = stats?.inactivity_threshold || 180;
  const isActive = daysSinceLastMatch !== undefined && daysSinceLastMatch !== null && daysSinceLastMatch <= threshold;
  
  return (
    <div className="relative overflow-hidden rounded-xl border border-white/10 p-8">
      {/* Background Base */}
      <div className="absolute inset-0 bg-neutral-950 z-0 rounded-[inherit]" />
      
      {/* The Flag Backdrop */}
      {countryCode && !loading && (
        <div 
          className="absolute top-1/2 -translate-y-1/2 right-0 w-1/2 h-[125%] z-32 opacity-60 select-none pointer-events-none rounded-[inherit]"
          style={{
            backgroundImage: `url(https://flagcdn.com/w640/${countryCode.toLowerCase()}.png)`,
            backgroundSize: '100% 100%',
            backgroundRepeat: 'no-repeat',
            filter: 'blur(10px)',
            maskImage: 'linear-gradient(to right, transparent, black 60%)',
            WebkitMaskImage: 'linear-gradient(to right, transparent, black 60%)'
          }}
        />
      )}
      
      {/* Texture Overlay (Grain/Noise) */}
      <div className="absolute inset-0 z-0 opacity-[0.03] pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] rounded-[inherit]" />
      
      {/* Fractal Crystalline Texture (Hexagonal overlay) */}
      {stats?.current_rank === 1 && !loading && (
        <motion.div 
          className="absolute inset-0 pointer-events-none opacity-[0.03] rounded-[inherit]"
          style={{ 
            backgroundImage: "url(\"data:image/svg+xml;utf8,<svg width='100%' height='100%' xmlns='http://www.w3.org/2000/svg'><defs><pattern id='hexPattern' width='50' height='43.3' patternUnits='userSpaceOnUse'><path d='M25 0 L50 14.43 v28.87 L25 57.73 L0 43.3 V14.43 Z' fill='none' stroke='rgba(255,255,255,0.8)' stroke-width='1'/></pattern></defs><rect width='100%' height='100%' fill='url(%23hexPattern)' /></svg>\")",
            backgroundSize: '50px 43.3px',
            zIndex: 31
          }}
          animate={{ backgroundPosition: ["0px 0px", "100px 86.6px"] }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        />
      )}
      
      {/* Wave Pattern for Top 2-3 */}
      {(stats?.current_rank === 2 || stats?.current_rank === 3) && !loading && (
        <motion.div 
          className="absolute inset-0 pointer-events-none opacity-[0.03] rounded-[inherit]"
          style={{ 
            backgroundImage: "url(\"data:image/svg+xml;utf8,<svg width='100%' height='100%' xmlns='http://www.w3.org/2000/svg'><defs><pattern id='wavePattern' width='100' height='20' patternUnits='userSpaceOnUse'><path d='M0,10 Q25,0 50,10 T100,10' fill='none' stroke='rgba(255,255,255,0.8)' stroke-width='1'/></pattern></defs><rect width='100%' height='100%' fill='url(%23wavePattern)' /></svg>\")",
            backgroundSize: '100px 20px',
            zIndex: 31
          }}
          animate={{ backgroundPosition: ["0px 0px", "100px 0px"] }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        />
      )}
      
      {/* Diagonal Pattern for Top 4-10 */}
      {(!!stats?.current_rank && stats.current_rank >= 4 && stats.current_rank <= 10) && !loading && (
        <motion.div 
          className="absolute inset-0 pointer-events-none opacity-[0.03] rounded-[inherit]"
          style={{ 
            backgroundImage: "url(\"data:image/svg+xml;utf8,<svg width='100%' height='100%' xmlns='http://www.w3.org/2000/svg'><defs><pattern id='diagPattern' width='20' height='20' patternUnits='userSpaceOnUse'><line x1='0' y1='20' x2='20' y2='0' stroke='rgba(255,255,255,0.8)' stroke-width='1'/></pattern></defs><rect width='100%' height='100%' fill='url(%23diagPattern)' /></svg>\")",
            backgroundSize: '20px 20px',
            zIndex: 31
          }}
          animate={{ backgroundPosition: ["0px 0px", "20px 20px"] }}
          transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
        />
      )}
      
      {/* Moving Outline Beams */}
      <div className="absolute inset-0 z-30 rounded-[inherit]">
        <BorderBeam duration={12} delay={0} colorFrom={colors.from} colorMiddle={colors.middle} colorTo={colors.to} />
        <BorderBeam duration={12} delay={4} colorFrom={colors.from} colorMiddle={colors.middle} colorTo={colors.to} />
        <BorderBeam duration={12} delay={8} colorFrom={colors.from} colorMiddle={colors.middle} colorTo={colors.to} />
      </div>
      
      {/* Content */}
      <div className="relative z-40 flex flex-col md:flex-row items-start md:items-center gap-4">
        <div className="flex flex-col gap-2 w-full">
          <div className="flex items-center gap-3">
            {loading ? (
              <div className="h-4 w-24 bg-zinc-800/60 animate-pulse rounded" />
            ) : (
              <div className="text-zinc-500 text-sm font-mono uppercase tracking-widest">{player?.country}</div>
            )}
            {loading ? (
              <div className="h-5 w-16 bg-zinc-800/60 animate-pulse rounded-full" />
            ) : daysSinceLastMatch !== undefined && daysSinceLastMatch !== null && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-zinc-950/80 rounded-full border border-zinc-800/80 text-[10px] font-bold font-mono">
                <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-500'}`} />
                <span className={isActive ? 'text-emerald-500' : 'text-zinc-500'}>
                  {isActive ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
            )}
          </div>
          
          {loading ? (
            <div className="h-10 w-72 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <NameShine 
              name={player?.name || 'Player'} 
              isTop1={stats?.current_rank === 1} 
              isTop23={stats?.current_rank === 2 || stats?.current_rank === 3} 
              isRank4_10={!!stats?.current_rank && stats.current_rank >= 4 && stats.current_rank <= 10} 
              isRank11_20={!!stats?.current_rank && stats.current_rank >= 11 && stats.current_rank <= 20} 
              isRank21_50={!!stats?.current_rank && stats.current_rank >= 21 && stats.current_rank <= 50} 
              isRank51_100={!!stats?.current_rank && stats.current_rank >= 51 && stats.current_rank <= 100} 
            />
          )}
          
          {loading ? (
            <div className="h-4 w-36 bg-zinc-800/60 animate-pulse rounded mt-2" />
          ) : (
            <div className="text-zinc-400 text-sm mt-1 flex items-center gap-2">
              <span>{player?.disciplines?.join(', ')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
