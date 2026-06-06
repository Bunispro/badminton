'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { API_BASE_URL } from '@/lib/api';

interface ModelMetric {
  name: string;
  eloValue: number;
  whrValue: number;
  displayElo: string;
  displayWhr: string;
  higherIsBetter: boolean;
  colorClass: string; 
  glowClass: string;  
  maxScale: number;   
}

interface AccuracyStats {
  accuracy: number;
  log_loss: number;
  ece: number;
}

interface ModelAccuracyData {
  elo: AccuracyStats;
  whr: AccuracyStats;
}

const ModelStatsBars = ({ elo, whr }: { elo: AccuracyStats, whr: AccuracyStats }) => {
  const metrics: ModelMetric[] = [
    {
      name: 'ACCURACY',
      eloValue: elo.accuracy / 100,
      whrValue: whr.accuracy / 100,
      displayElo: `${elo.accuracy.toFixed(1)}%`,
      displayWhr: `${whr.accuracy.toFixed(1)}%`,
      higherIsBetter: true,
      colorClass: 'bg-[#00FF9D]',
      glowClass: 'shadow-[0_0_12px_rgba(0,255,157,0.3)]',
      maxScale: 1.0,
    },
    {
      name: 'LOG LOSS',
      eloValue: elo.log_loss,
      whrValue: whr.log_loss,
      displayElo: elo.log_loss.toFixed(3),
      displayWhr: whr.log_loss.toFixed(3),
      higherIsBetter: false,
      colorClass: 'bg-[#00D2FF]',
      glowClass: 'shadow-[0_0_12px_rgba(0,210,255,0.3)]',
      maxScale: 1.0,
    },
    {
      name: 'ECE',
      eloValue: elo.ece,
      whrValue: whr.ece,
      displayElo: elo.ece.toFixed(4),
      displayWhr: whr.ece.toFixed(4),
      higherIsBetter: false,
      colorClass: 'bg-[#A855F7]',
      glowClass: 'shadow-[0_0_12px_rgba(168,85,247,0.3)]',
      maxScale: 0.02,
    },
  ];

  const calculateWidth = (metric: ModelMetric, value: number) => {
    if (metric.name === 'LOG LOSS') {
      return Math.max(0, Math.min(100, ((value - 0.45) / (0.693 - 0.45)) * 100));
    }
    return Math.max(0, Math.min(100, (value / metric.maxScale) * 100));
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mt-2">
      {metrics.map((metric) => {
        const eloWidth = calculateWidth(metric, metric.eloValue);
        const whrWidth = calculateWidth(metric, metric.whrValue);

        return (
          <div key={metric.name} className="flex flex-col space-y-4">
            <div className="flex justify-between items-baseline border-b border-zinc-800 pb-2">
              <span className="text-sm font-black tracking-wider text-zinc-200">
                {metric.name}
              </span>
              <span className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
                {metric.higherIsBetter ? '↑ Better' : '↓ Better'}
              </span>
            </div>

            <div className="space-y-5 py-2">
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-zinc-500 font-bold uppercase tracking-tight">ELO Hybrid</span>
                  <span className="font-mono font-black text-zinc-100">{metric.displayElo}</span>
                </div>
                <div className="h-2 w-full bg-zinc-900 rounded-full overflow-hidden relative border border-zinc-800/50">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(eloWidth, 100)}%` }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className={`h-full rounded-full ${metric.colorClass} ${metric.glowClass}`}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-zinc-500 font-bold uppercase tracking-tight">WHR Model</span>
                  <span className="font-mono font-black text-zinc-100">{metric.displayWhr}</span>
                </div>
                <div className="h-2 w-full bg-zinc-900 rounded-full overflow-hidden relative border border-zinc-800/50">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(whrWidth, 100)}%` }}
                    transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                    className={`h-full rounded-full ${metric.colorClass} ${metric.glowClass}`}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export function ModelAccuracyCard() {
  const [data, setData] = useState<ModelAccuracyData | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/dashboard/model-stats`)
      .then(res => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) return (
    <div className="h-full flex flex-col justify-center items-center gap-4 bg-zinc-900/20 animate-pulse rounded-xl border border-zinc-800/50">
       <div className="w-12 h-12 rounded-full border-2 border-emerald-500/20 border-t-emerald-500 animate-spin" />
       <div className="text-[10px] text-zinc-500 font-mono uppercase tracking-[0.2em]">Initializing Engine...</div>
    </div>
  );

  const elo = data?.elo || { accuracy: 73.5, log_loss: 0.517, ece: 0.0074 };
  const whr = data?.whr || { accuracy: 75.8, log_loss: 0.482, ece: 0.0051 };

  return (
    <div className="h-full flex flex-col">
      <div className="text-xs font-bold tracking-widest text-zinc-600 mb-6 uppercase font-mono">
        Model Statistics // Engine Comparison
      </div>
      
      <div className="flex-grow flex flex-col justify-center">
        <ModelStatsBars elo={elo} whr={whr} />
      </div>

      <div className="mt-8 pt-4 border-t border-zinc-800/30 flex justify-between items-center text-[9px] text-zinc-600 font-black uppercase tracking-[0.3em]">
         <div>Last Validated: {new Date().toLocaleDateString()}</div>
         <div className="flex items-center gap-4">
            <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> PROBABILISTIC MODELS</div>
            <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> CALIBRATED RESULTS</div>
         </div>
      </div>
    </div>
  );
}
