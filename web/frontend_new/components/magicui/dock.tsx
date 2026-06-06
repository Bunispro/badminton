'use client';

import React from 'react';
import { motion } from 'framer-motion';

export function Dock({ children, className }: { children: React.ReactNode, className?: string }) {
  return (
    <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 ${className}`}>
      <div className="flex items-center gap-2 px-4 py-3 bg-zinc-900/80 backdrop-blur-xl border border-zinc-800/50 rounded-2xl shadow-[0_0_40px_rgba(0,0,0,0.5)]">
        {children}
      </div>
    </div>
  );
}

export function DockIcon({ children, label, active, onClick }: { children: React.ReactNode, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <div className="relative group">
      <motion.button
        whileHover={{ scale: 1.1, y: -4 }}
        whileTap={{ scale: 0.95 }}
        onClick={onClick}
        className={`w-12 h-12 flex items-center justify-center rounded-xl transition-colors ${
          active ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white border border-transparent'
        }`}
      >
        {children}
      </motion.button>
      <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 bg-zinc-800 text-[10px] font-bold text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        {label}
      </div>
    </div>
  );
}
