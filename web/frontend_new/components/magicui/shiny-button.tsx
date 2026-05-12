'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ShinyButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

export function ShinyButton({ children, className, ...props }: ShinyButtonProps) {
  return (
    <button
      className={`px-4 py-2 bg-zinc-100 text-zinc-900 hover:bg-zinc-300 shadow-[0_0_15px_rgba(255,255,255,0.1)] transition-all font-semibold rounded-lg relative overflow-hidden group ${className}`}
      {...props}
    >
      {/* Shiny effect overlay using Framer Motion */}
      <motion.span
        className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent"
        initial={{ x: '-100%' }}
        whileHover={{ x: '100%' }}
        transition={{ duration: 0.5, ease: 'easeInOut' }}
      />
      <span className="relative z-10">{children}</span>
    </button>
  );
}
