import React from 'react';
import { motion } from 'framer-motion';

export const NameShine = React.memo(({ name, isTop1, isTop23, isRank4_10, isRank11_20, isRank21_50, isRank51_100 }: { name: string, isTop1?: boolean, isTop23?: boolean, isRank4_10?: boolean, isRank11_20?: boolean, isRank21_50?: boolean, isRank51_100?: boolean }) => {
  if (isTop1) {
    return (
      <h1 className="relative text-5xl font-bold uppercase tracking-tighter inline-block cursor-default">
        {/* Outer Glow (Internal Glow Animation) */}
        <motion.span
          className="absolute inset-0 text-transparent pointer-events-none"
          animate={{ 
            filter: [
              "drop-shadow(0 0 10px rgba(239,68,68,0.6))", 
              "drop-shadow(0 0 30px rgba(239,68,68,1))", 
              "drop-shadow(0 0 10px rgba(239,68,68,0.6))"
            ] 
          }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        >
          {name}
        </motion.span>

        {/* Base text with Ruby Gradient */}
        <span 
          className="bg-gradient-to-b from-[#7f1d1d] to-[#ef4444] bg-clip-text text-transparent drop-shadow-md relative"
        >
          {name}
        </span>
        
        {/* Low-poly Texture (SVG Mask simulation) */}
        <span 
          className="absolute inset-0 bg-clip-text text-transparent pointer-events-none opacity-70" 
          style={{ 
            backgroundImage: `url("data:image/svg+xml;utf8,<svg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><polygon points='0,0 50,0 25,50' fill='%23ef4444' opacity='0.2'/><polygon points='50,0 100,0 75,50' fill='%23ef4444' opacity='0.4'/><polygon points='25,50 75,50 50,100' fill='%237f1d1d' opacity='0.3'/><polygon points='0,0 25,50 0,100' fill='%237f1d1d' opacity='0.15'/><polygon points='100,0 75,50 100,100' fill='%23ef4444' opacity='0.5'/></svg>")`,
            backgroundSize: '40px 40px'
          }}
        >
          {name}
        </span>

        {/* Diagonal Sweep (45-degree) */}
        <motion.span 
          className="absolute inset-0 bg-clip-text text-transparent pointer-events-none"
          style={{ 
            backgroundImage: 'linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.2) 50%, transparent 60%)',
            backgroundSize: '400% 400%',
          }}
          animate={{ backgroundPosition: ['300% 300%', '-100% -100%'] }}
          transition={{ duration: 4, repeat: Infinity, repeatDelay: 2, ease: "linear" }}
        >
          {name}
        </motion.span>
      </h1>
    );
  }

  if (isTop23) {
    return (
      <h1 className="relative text-5xl font-bold uppercase tracking-tighter inline-block cursor-default">
        {/* Outer Neon Bloom (Static) */}
        <span
          className="absolute inset-0 text-transparent pointer-events-none"
          style={{ 
            textShadow: '0 0 15px #3b82f6',
          }}
        >
          {name}
        </span>

        {/* Base text with Caustics/Liquid effect and Sparkle Animation */}
        <div className="relative flex">
          {name.split('').map((char, index) => (
            <motion.span
              key={index}
              className="relative inline-block"
              animate={{ 
                scale: [1, 1.05, 1],
                filter: ["brightness(1)", "brightness(1.4)", "brightness(1)"]
              }}
              transition={{ 
                duration: 0.8, 
                repeat: Infinity, 
                repeatDelay: 3 + (index % 4) * 0.7, // Safe for SSR, looks random
                delay: index * 0.1
              }}
              style={{ display: 'inline-block' }}
            >
              {/* Base Gradient */}
              <span className="bg-gradient-to-b from-[#1e3a8a] to-[#3b82f6] bg-clip-text text-transparent drop-shadow-md">
                {char === ' ' ? '\u00A0' : char}
              </span>
              
              {/* Caustics Overlay (Moving Water) */}
              <motion.span 
                className="absolute inset-0 bg-clip-text text-transparent opacity-40" 
                style={{ 
                  backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.8) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.8) 0%, transparent 50%)',
                  backgroundSize: '200% 200%'
                }}
                animate={{ 
                  backgroundPosition: ['0% 0%', '100% 100%', '0% 0%']
                }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              >
                {char === ' ' ? '\u00A0' : char}
              </motion.span>
            </motion.span>
          ))}
        </div>
      </h1>
    );
  }

  if (isRank4_10) {
    return (
      <h1 className="relative text-5xl font-bold uppercase tracking-tighter inline-block cursor-default">
        {/* Chrome Stroke Layer (Behind) */}
        <span 
          className="absolute inset-0 text-transparent pointer-events-none"
          style={{ 
            WebkitTextStroke: '1px #10b981',
          }}
        >
          {name}
        </span>

        {/* Base text (Mint to Deep Forest) */}
        <span 
          className="bg-gradient-to-b from-[#6EE7B7] to-[#064E3B] bg-clip-text text-transparent drop-shadow-md relative"
          style={{ textShadow: '0 1px 1px rgba(255,255,255,0.3)' }}
        >
          {name}
        </span>

        {/* Parallax Layer 1 (Moving Right) */}
        <motion.span 
          className="absolute inset-0 bg-gradient-to-r from-transparent via-[#6EE7B7]/50 to-transparent bg-clip-text text-transparent pointer-events-none"
          style={{ 
            backgroundSize: '200% 100%',
          }}
          animate={{ backgroundPosition: ['0% 0%', '200% 0%'] }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        >
          {name}
        </motion.span>
        
        {/* Parallax Layer 2 (Moving Left, faster) */}
        <motion.span 
          className="absolute inset-0 bg-gradient-to-l from-transparent via-white/30 to-transparent bg-clip-text text-transparent pointer-events-none"
          style={{ 
            backgroundSize: '300% 100%',
          }}
          animate={{ backgroundPosition: ['300% 0%', '0% 0%'] }}
          transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        >
          {name}
        </motion.span>
      </h1>
    );
  }

  if (isRank11_20) {
    return (
      <h1 className="relative text-5xl font-bold uppercase tracking-tighter inline-block cursor-default group">
        <span className="bg-gradient-to-b from-purple-400 to-indigo-600 bg-clip-text text-transparent relative z-10 transition-all duration-300">
          {name}
        </span>
        <motion.span 
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent bg-clip-text text-transparent z-20 pointer-events-none"
          animate={{ x: ['-100%', '200%'] }}
          transition={{ duration: 2.5, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
        >
          {name}
        </motion.span>
        <span className="absolute inset-0 bg-indigo-500/20 blur-md -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          {name}
        </span>
      </h1>
    );
  }

  if (isRank21_50) {
    return (
      <h1 className="relative text-5xl font-bold uppercase tracking-tighter inline-block cursor-default group">
        <span className="bg-gradient-to-br from-zinc-300 via-zinc-400 to-zinc-600 bg-clip-text text-transparent drop-shadow-sm transition-colors duration-300 group-hover:from-zinc-100 group-hover:to-zinc-400">
          {name}
        </span>
        <span className="absolute inset-0 text-transparent pointer-events-none transition-all duration-300 opacity-0 group-hover:opacity-100" style={{ WebkitTextStroke: '1px rgba(255,255,255,0.2)' }}>
          {name}
        </span>
      </h1>
    );
  }

  if (isRank51_100) {
    return (
      <h1 className="relative text-4xl font-bold uppercase tracking-tighter inline-block cursor-default text-zinc-500 hover:text-zinc-300 transition-colors duration-300">
        {name}
      </h1>
    );
  }

  // Base Top 100+ Name
  return (
    <h1 className="relative text-3xl font-bold uppercase tracking-tighter inline-block cursor-default text-zinc-600">
      {name}
    </h1>
  );
});

NameShine.displayName = 'NameShine';
