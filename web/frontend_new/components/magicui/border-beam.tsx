'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface BorderBeamProps {
  duration?: number;
  className?: string;
}

export function BorderBeam({ duration = 15, className }: BorderBeamProps) {
  return (
    <div className={`absolute inset-0 pointer-events-none rounded-lg overflow-hidden ${className}`}>
      {/* The moving beam */}
      <motion.div
        className="absolute inset-[-100%] bg-[conic-gradient(from_0deg,transparent_60%,#10b981_80%,transparent)]"
        animate={{ rotate: 360 }}
        transition={{ duration: duration, repeat: Infinity, ease: "linear" }}
      />
      {/* The mask to make it a border (assumes card bg is zinc-900) */}
      <div className="absolute inset-[1px] bg-zinc-900 rounded-lg" />
    </div>
  );
}
