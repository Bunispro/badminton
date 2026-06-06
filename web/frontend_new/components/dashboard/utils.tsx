'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import countryCodes from '@/lib/countryCodes.json';

export const getCountryCode = (countryName: string) => {
  if (!countryName) return null;
  const trimmed = countryName.trim();
  return (countryCodes as Record<string, string>)[trimmed] || trimmed || null;
};

export const formatEliteName = (name: string, isDoubles: boolean = false) => {
  if (!name) return { lines: [], typography: "text-6xl leading-none font-black uppercase" };

  const parts = name.trim().split(/\s+/);
  const p = [...parts];
  const threshold = 9;

  if (p[0].length > threshold) {
    p[0] = `${p[0].charAt(0)}.`;
  }

  if (isDoubles && p.length > 1 && p[1].length > 12) {
    p[0] = `${p[0].charAt(0)}.`;
  }

  let lines: string[] = [];
  if (isDoubles) {
    lines = [p[0], p.slice(1).join(" ")];
  } else {
    if (p.length === 3) {
      lines = p;
    } else {
      lines = [p[0], p.slice(1).join(" ")];
    }
  }

  const longest = Math.max(...lines.map(l => l.length));
  let typography = "text-6xl leading-none font-black uppercase";

  if (longest > 12) {
    typography = "text-3xl leading-tight tracking-tighter font-black uppercase";
  } else if (longest >= 10) {
    typography = "text-4xl leading-none tracking-tight font-black uppercase";
  }

  return { lines, typography };
};

interface Segment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
}

export const LightningStrike = React.memo(({ id }: { id: number | string }) => {
  const [bolts, setBolts] = useState<Segment[][]>([]);
  const [delays, setDelays] = useState<{ repeat: number, initial: number } | null>(null);

  useEffect(() => {
    const rd = Math.random() * 2 + 2; // Repeat delay of 2 to 4 seconds
    const idelay = Math.random() * 1.5; // Initial delay of 0 to 1.5 seconds
    setDelays({ repeat: rd, initial: idelay });

    const generateStrike = () => {
      const boltCount = 2 + Math.floor(Math.random() * 3);
      const newStrikeBolts = [];
      for (let b = 0; b < boltCount; b++) {
        const allSegments: Segment[] = [];
        const edge = Math.floor(Math.random() * 4);
        let sx, sy, initialAngle;
        if (edge === 0) { sx = Math.random() * 100; sy = 0; initialAngle = Math.PI / 2 + (Math.random() - 0.5); }
        else if (edge === 1) { sx = Math.random() * 100; sy = 100; initialAngle = -Math.PI / 2 + (Math.random() - 0.5); }
        else if (edge === 2) { sx = 0; sy = Math.random() * 100; initialAngle = 0 + (Math.random() - 0.5); }
        else { sx = 100; sy = Math.random() * 100; initialAngle = Math.PI + (Math.random() - 0.5); }

        const segmentCount = 3 + Math.floor(Math.random() * 4);
        const baseWidth = 2.5 + Math.random() * 2.0;

        const generateSegments = (startPosX: number, startPosY: number, angle: number, count: number, startIdx: number, bWidth: number, depth: number = 0) => {
          if (depth > 1) return;
          let cx = startPosX; let cy = startPosY; let ca = angle;
          for (let j = 0; j < count; j++) {
            const targetLen = 8 + Math.random() * 12;
            ca += (Math.random() - 0.5) * (Math.PI / 1.1);
            const microSteps = 5 + Math.floor(Math.random() * 4);
            let lx = cx; let ly = cy;
            for (let k = 1; k <= microSteps; k++) {
              const stepLen = targetLen / microSteps;
              const microAngle = ca + (Math.random() - 0.5) * (Math.PI / 1.8);
              const curX = lx + Math.cos(microAngle) * stepLen;
              const curY = ly + Math.sin(microAngle) * stepLen;
              allSegments.push({ x1: lx, y1: ly, x2: curX, y2: curY, width: bWidth * Math.pow(0.80, startIdx + j) });
              lx = curX; ly = curY;
            }
            cx = lx; cy = ly;
            if (Math.random() > 0.8 && depth < 1) {
              generateSegments(cx, cy, ca + (Math.random() > 0.5 ? 0.9 : -0.9), 2, startIdx + j + 1, bWidth * 0.7, depth + 1);
            }
          }
        };
        generateSegments(sx, sy, initialAngle, segmentCount, 0, baseWidth);
        newStrikeBolts.push(allSegments);
      }
      return newStrikeBolts;
    };
    setBolts(generateStrike());
  }, [id]);

  if (!delays || bolts.length === 0) return null;

  return (
    <motion.g
      className="mix-blend-plus-lighter"
      style={{ filter: 'drop-shadow(0 0 4px #fbbf24) drop-shadow(0 0 12px #f59e0b) drop-shadow(0 0 25px #d97706)' }}
    >
      {bolts.map((bolt, bIdx) => (
        <g key={bIdx}>
          {bolt.map((seg, idx) => {
            const appearanceDelay = idx * 0.015;
            const fadeOutStart = 0.28 + (idx * 0.001);
            const fadeOutEnd = 0.33 + (idx * 0.001);
            return (
              <motion.line
                key={idx}
                x1={`${seg.x1}%`}
                y1={`${seg.y1}%`}
                x2={`${seg.x2}%`}
                y2={`${seg.y2}%`}
                stroke="#fbbf24"
                strokeWidth={seg.width}
                strokeLinecap="butt"
                strokeLinejoin="miter"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 1, 1, 0] }}
                transition={{
                  duration: 1.5,
                  times: [
                    0,
                    Math.min(0.08, 0.02 + appearanceDelay),
                    Math.max(0.10, fadeOutStart),
                    Math.max(0.12, fadeOutEnd)
                  ],
                  repeat: Infinity,
                  repeatDelay: delays.repeat,
                  delay: delays.initial,
                  ease: "easeOut"
                }}
                style={{ vectorEffect: 'non-scaling-stroke' }}
              />
            );
          })}
        </g>
      ))}
    </motion.g>
  );
});
LightningStrike.displayName = 'LightningStrike';
