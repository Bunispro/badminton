'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface AnimatedBeamProps {
  duration?: number;
  opacity?: number;
  className?: string;
  color?: string;
  thickness?: number;
}

export function AnimatedBeam({ 
  duration = 2, 
  opacity = 1, 
  className = "", 
  color = "#22d3ee",
  thickness = 2
 }: AnimatedBeamProps) {
  return (
    <div className={`relative flex items-center justify-center w-full h-full ${className}`}>
      {/* The Line */}
      <div className="absolute w-full opacity-20" style={{ height: `${thickness}px`, backgroundColor: color }} />
      
      {/* The Animated Beam */}
      <div className="relative w-full overflow-hidden rounded-full" style={{ height: `${thickness * 3}px` }}>
        <motion.div
          className="absolute h-full"
          style={{ 
            width: '30%',
            background: `linear-gradient(90deg, transparent, ${color}, #fff, ${color}, transparent)`,
            opacity: opacity,
            filter: `blur(${thickness}px) drop-shadow(0 0 ${thickness * 4}px ${color})`
          }}
          animate={{ x: ['-100%', '400%'] }}
          transition={{ 
            duration: duration, 
            repeat: Infinity, 
            ease: 'linear' 
          }}
        />
        
        {/* Intense Core */}
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 h-[2px]"
          style={{ 
            width: '15%',
            background: `linear-gradient(90deg, transparent, #fff, transparent)`,
            opacity: opacity,
            boxShadow: `0 0 ${thickness * 5}px #fff`
          }}
          animate={{ x: ['-150%', '600%'] }}
          transition={{ 
            duration: duration * 0.7, 
            repeat: Infinity, 
            ease: 'linear' 
          }}
        />
      </div>
    </div>
  );
}
