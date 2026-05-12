'use client';

import React from 'react';
import { motion } from 'framer-motion';

export function AnimatedBeam() {
  return (
    <div className="flex items-center justify-between w-full max-w-lg mx-auto bg-zinc-900/50 backdrop-blur-sm p-6 rounded-lg border border-zinc-800 relative">
      <div className="flex flex-col items-center gap-2 z-10">
        <div className="w-12 h-12 bg-zinc-800 rounded-full flex items-center justify-center border border-zinc-700 shadow-lg">
          {/* Match Results Icon */}
          <svg className="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        </div>
        <span className="text-xs font-medium text-zinc-400">Match Results</span>
      </div>

      {/* The Line and Beam */}
      <div className="flex-grow h-0.5 bg-zinc-800 mx-4 relative overflow-hidden">
        <motion.div
          className="absolute inset-y-0 bg-gradient-to-r from-transparent via-cyan-400 to-transparent w-1/3"
          animate={{ x: ['-100%', '300%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      <div className="flex flex-col items-center gap-2 z-10">
        <div className="w-12 h-12 bg-zinc-800 rounded-full flex items-center justify-center border border-zinc-700 shadow-lg">
          {/* Rating Engine Icon */}
          <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        </div>
        <span className="text-xs font-medium text-zinc-400">Rating Engine</span>
      </div>
    </div>
  );
}
