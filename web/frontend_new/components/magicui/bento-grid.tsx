import React from 'react';

export function BentoGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl mx-auto">
      {children}
    </div>
  );
}

export function BentoCard({ className, children }: { className?: string, children: React.ReactNode }) {
  return (
    <div className={`bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-lg p-6 hover:border-zinc-700 transition-colors duration-300 flex flex-col justify-between ${className}`}>
      {children}
    </div>
  );
}
