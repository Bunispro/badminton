'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '@/lib/api';
import { useThrottledCallback } from '@/hooks/use-throttled-callback';

interface ShapImportance {
  feature: string;
  importance: number;
  color: string;
}

const DEFAULT_SHAP: Record<string, ShapImportance[]> = {
  MS: [
    { feature: "Skill", importance: 57.4, color: "#38bdf8" },
    { feature: "Synergy", importance: 11.8, color: "#10b981" },
    { feature: "Conditions", importance: 17.3, color: "#f59e0b" },
    { feature: "Rest", importance: 10.7, color: "#8b5cf6" },
    { feature: "H2H", importance: 2.9, color: "#ec4899" }
  ],
  WS: [
    { feature: "Skill", importance: 57.9, color: "#38bdf8" },
    { feature: "Synergy", importance: 11.7, color: "#10b981" },
    { feature: "Conditions", importance: 17.4, color: "#f59e0b" },
    { feature: "Rest", importance: 9.2, color: "#8b5cf6" },
    { feature: "H2H", importance: 3.8, color: "#ec4899" }
  ],
  MD: [
    { feature: "Skill", importance: 50.6, color: "#38bdf8" },
    { feature: "Synergy", importance: 21.6, color: "#10b981" },
    { feature: "Conditions", importance: 18.1, color: "#f59e0b" },
    { feature: "Rest", importance: 7.1, color: "#8b5cf6" },
    { feature: "H2H", importance: 2.6, color: "#ec4899" }
  ],
  WD: [
    { feature: "Skill", importance: 49.5, color: "#38bdf8" },
    { feature: "Synergy", importance: 21.3, color: "#10b981" },
    { feature: "Conditions", importance: 18.4, color: "#f59e0b" },
    { feature: "Rest", importance: 7.7, color: "#8b5cf6" },
    { feature: "H2H", importance: 3.1, color: "#ec4899" }
  ],
  XD: [
    { feature: "Skill", importance: 49.8, color: "#38bdf8" },
    { feature: "Synergy", importance: 22.4, color: "#10b981" },
    { feature: "Conditions", importance: 17.3, color: "#f59e0b" },
    { feature: "Rest", importance: 8.1, color: "#8b5cf6" },
    { feature: "H2H", importance: 2.4, color: "#ec4899" }
  ]
};

export function OverallShapCard() {
  const [activeEvent, setActiveEvent] = useState<string>('MS');
  const [shapData, setShapData] = useState<Record<string, ShapImportance[]>>(DEFAULT_SHAP);
  const [loading, setLoading] = useState(true);

  const throttledSetActiveEvent = useThrottledCallback((ev: string) => {
    setActiveEvent(ev);
  }, 200);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/dashboard/model-stats`)
      .then(res => res.json())
      .then(data => {
        if (!active) return;
        if (data.shap && typeof data.shap === 'object' && !Array.isArray(data.shap)) {
          setShapData(data.shap);
        } else {
          setShapData(DEFAULT_SHAP);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching overall SHAP stats:", err);
        if (active) {
          setShapData(DEFAULT_SHAP);
          setLoading(false);
        }
      });
    return () => { active = false; };
  }, []);

  const rawItems = shapData[activeEvent] || DEFAULT_SHAP[activeEvent] || [];
  
  // Filter out Synergy for singles events (MS, WS)
  const isSingles = activeEvent === 'MS' || activeEvent === 'WS';
  const filteredItems = isSingles 
    ? rawItems.filter(item => item.feature !== 'Synergy') 
    : rawItems;
    
  // Redistribute percentages so they sum to exactly 100%
  const totalRawImportance = filteredItems.reduce((sum, item) => sum + item.importance, 0);
  const items = filteredItems.map(item => ({
    ...item,
    importance: totalRawImportance > 0 ? (item.importance / totalRawImportance) * 100 : item.importance
  }));

  const events = ['MS', 'WS', 'MD', 'WD', 'XD'];

  return (
    <div className="h-full flex flex-col justify-between py-1 relative group overflow-hidden">
      <div className="absolute -inset-2 bg-sky-500/5 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
      
      <div className="flex flex-col gap-0.5 relative z-20 mb-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
            Feature Importance
          </span>
          <div className="flex items-center bg-zinc-950/80 rounded-md p-0.5 border border-zinc-800/50 shrink-0 relative z-30">
             {events.map(ev => (
               <button 
                 key={ev} 
                 onClick={() => throttledSetActiveEvent(ev)} 
                 className={`px-1.5 py-0.5 text-[8.5px] font-black rounded transition-all ${activeEvent === ev ? 'bg-sky-500/20 text-sky-400 font-bold' : 'text-zinc-600 hover:text-zinc-400'} cursor-pointer`}
               >
                 {ev}
               </button>
             ))}
          </div>
        </div>
      </div>

      <div className="flex-grow flex flex-col justify-center my-auto min-h-[140px] pt-4">
        <AnimatePresence mode="wait">
          <motion.div 
            key={activeEvent}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="flex-grow flex flex-col justify-center gap-2 my-auto relative z-10 pb-1"
          >
            {items.map((item, index) => (
              <div key={item.feature} className="space-y-0.5">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-zinc-400 font-bold uppercase tracking-tight">{item.feature}</span>
                  <span className="font-mono font-black text-zinc-200">{item.importance.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden relative border border-zinc-800/50">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${item.importance}%` }}
                    transition={{ duration: 1.2, ease: "easeOut", delay: index * 0.05 }}
                    style={{ backgroundColor: item.color }}
                    className="h-full rounded-full shadow-[0_0_8px_rgba(255,255,255,0.05)]"
                  />
                </div>
              </div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="h-[2px] w-full bg-zinc-900 rounded-full mt-2" />
    </div>
  );
}
