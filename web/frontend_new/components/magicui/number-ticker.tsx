'use client';

import { useEffect, useRef } from "react";
import { animate } from "framer-motion";

interface NumberTickerProps {
  value: number;
  className?: string;
}

export function NumberTicker({ value, className }: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (node) {
      const controls = animate(0, value, {
        duration: 2,
        ease: "easeOut",
        onUpdate(latest) {
          node.textContent = Math.round(latest).toString();
        },
      });

      return () => controls.stop();
    }
  }, [value]);

  return <span ref={ref} className={`font-mono text-zinc-100 ${className}`}>0</span>;
}
