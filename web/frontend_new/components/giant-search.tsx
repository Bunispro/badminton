'use client';

import { useState, useEffect, useRef } from 'react';
import { Command } from 'cmdk';
import { useRouter } from 'next/navigation';
import Flag from 'react-flagpack';
import 'react-flagpack/dist/style.css';
import countryCodes from '@/lib/countryCodes.json';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '@/lib/api';


const getCountryCode = (countryName: string) => {
  return (countryCodes as Record<string, string>)[countryName] || countryName || null;
};

interface SearchResult {
  id: string;
  name: string;
  country: string;
  rating?: number;
}

export function GiantSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      return;
    }

    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    timeoutRef.current = setTimeout(() => {
      fetch(`${API_BASE_URL}/api/players/search?q=${query}`)
        .then(res => res.json())
        .then(data => {
          setResults(Array.isArray(data) ? data : []);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error searching players:", err);
          setLoading(false);
        });
    }, 300);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [query]);

  const onSelect = (id: string) => {
    setOpen(false);
    setQuery('');
    router.push(`/player/${id}`);
  };

  return (
    <div ref={containerRef} className="w-full max-w-3xl mx-auto relative z-30">
      <div className="text-center mb-8">
        <motion.h2 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-zinc-500 text-sm font-mono uppercase tracking-[0.2em] mb-2"
        >
          Search Analytics Database
        </motion.h2>
        <motion.h1 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-4xl md:text-6xl font-bold tracking-tight text-white"
        >
          Find Your <span className="text-cyan-400">Player.</span>
        </motion.h1>
      </div>

      <div className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-1000 group-focus-within:duration-200"></div>
        <Command 
          shouldFilter={false}
          className="relative bg-zinc-900/80 backdrop-blur-xl border border-zinc-800 rounded-2xl overflow-visible shadow-2xl"
        >
          <div className="flex items-center px-6 py-5">
            <svg className="w-6 h-6 text-zinc-500 mr-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            <Command.Input
              value={query}
              onValueChange={(val) => {
                setQuery(val);
                setOpen(true);
                if (val.length < 2) {
                  setResults([]);
                  setLoading(false);
                } else {
                  setLoading(true);
                }
              }}
              placeholder="Type player name (e.g. Viktor Axelsen)..."
              className="bg-transparent border-none focus:outline-none w-full text-xl text-zinc-100 placeholder-zinc-600"
            />
            {loading && (
              <div className="animate-spin h-5 w-5 border-2 border-cyan-500 border-t-transparent rounded-full ml-4"></div>
            )}
          </div>

          <AnimatePresence>
            {open && results.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute top-full left-0 w-full mt-4 bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl z-50 max-h-[400px] overflow-hidden"
              >
                <Command.List className="p-2 overflow-y-auto max-h-[380px]">
                  {results.map((item) => {
                    const countryCode = item.country ? getCountryCode(item.country) : null;
                    return (
                      <Command.Item
                        key={item.id}
                        value={item.name}
                        onSelect={() => onSelect(item.id)}
                        onClick={() => onSelect(item.id)}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          onSelect(item.id);
                        }}
                        className="flex items-center justify-between px-4 py-3 hover:bg-zinc-800/50 rounded-xl cursor-pointer transition-all group/item"
                      >
                        <div className="flex items-center gap-4">
                          {countryCode ? (
                            <div className="grayscale-[0.1] brightness-[0.9] rounded-md scale-110">
                              <Flag code={countryCode.toUpperCase()} size="S" />
                            </div>
                          ) : (
                            <div className="w-6 h-4 bg-zinc-800 rounded flex items-center justify-center text-[8px] text-zinc-600">??</div>
                          )}
                          <span className="text-lg font-medium text-zinc-100 group-hover/item:text-cyan-400 transition-colors">
                            {item.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          {item.rating && (
                            <span className="px-2 py-1 bg-zinc-800 text-zinc-400 rounded text-xs font-mono">
                              {Math.round(item.rating)}
                            </span>
                          )}
                          <svg className="w-4 h-4 text-zinc-600 opacity-0 group-hover/item:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                          </svg>
                        </div>
                      </Command.Item>
                    );
                  })}
                </Command.List>
              </motion.div>
            )}
          </AnimatePresence>
        </Command>
      </div>
    </div>
  );
}
