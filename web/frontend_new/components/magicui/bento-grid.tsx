import React from 'react';

export function BentoGrid({ children, className }: { children: React.ReactNode, className?: string }) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-7xl mx-auto px-4 ${className}`}>
      {children}
    </div>
  );
}

export function BentoCard({ className, children, overflow = true }: { className?: string, children: React.ReactNode, overflow?: boolean }) {
  return (
    <div className={`group relative bg-zinc-900/50 backdrop-blur-md border border-zinc-800/50 rounded-2xl p-6 ${overflow ? 'overflow-hidden' : ''} hover:border-zinc-700/50 transition-all duration-500 shadow-2xl ${className}`}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none rounded-2xl" />
      <div className="relative z-10 h-full">
        {children}
      </div>
    </div>
  );
}
