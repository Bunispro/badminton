'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface BorderBeamProps {
  duration?: number;
  className?: string;
  colorFrom?: string;
  colorMiddle?: string;
  colorTo?: string;
  delay?: number;
  size?: number;
  borderWidth?: number;
}

export function BorderBeam({ 
  duration = 15, 
  className, 
  colorFrom = "#10b981", 
  colorMiddle, 
  colorTo = "#10b981", 
  delay = 0,
  size = 300,
  borderWidth = 2
}: BorderBeamProps) {
  // Convert size to a degree spread
  const spread = Math.min(360, (size / 1000) * 360);

  return (
    <div 
      className={`absolute inset-0 pointer-events-none rounded-[inherit] overflow-hidden ${className}`}
      style={{
        WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        WebkitMaskComposite: 'xor',
        mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        maskComposite: 'exclude',
        padding: `${borderWidth}px`,
      } as React.CSSProperties}
    >
      <motion.div
        className="absolute inset-[-250%] aspect-square"
        style={{ 
          background: colorMiddle 
            ? `conic-gradient(from 0deg, ${colorFrom} 0deg, ${colorMiddle} ${spread/4}deg, ${colorTo} ${spread/2}deg, transparent ${spread}deg)`
            : `conic-gradient(from 0deg, ${colorFrom} 0deg, ${colorTo} ${spread/2}deg, transparent ${spread}deg)`,
          filter: "blur(0.5px)",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: duration, repeat: Infinity, ease: "linear", delay: delay }}
      />
    </div>
  );
}
