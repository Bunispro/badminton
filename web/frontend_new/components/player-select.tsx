'use client';

import { useState, useEffect, useRef } from 'react';
import { Command } from 'cmdk';
import { useVirtualizer } from '@tanstack/react-virtual';
import Flag from 'react-flagpack';
import 'react-flagpack/dist/style.css';
import countryCodes from '@/lib/countryCodes.json';
import React from 'react';
import { API_BASE_URL } from '@/lib/api';


const getCountryCode = (countryName: string) => {
  return (countryCodes as Record<string, string>)[countryName] || countryName || null;
};

export interface SelectablePlayer {
  player_id: string;
  name: string;
  country: string;
  rating?: number;
}

interface PlayerSelectProps {
  onSelect: (player: SelectablePlayer) => void;
  placeholder?: string;
  label?: string;
}

export function PlayerSelect({ onSelect, placeholder = "Search player...", label }: PlayerSelectProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SelectablePlayer[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
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

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (player: SelectablePlayer) => {
    onSelect(player);
    setOpen(false);
    setQuery('');
  };

  const rowVirtualizer = useVirtualizer({
    count: results.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 5,
  });

  return (
    <div className="relative w-full" ref={containerRef}>
      {label && <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">{label}</div>}
      <Command 
        shouldFilter={false} 
        className="bg-zinc-900/50 backdrop-blur-md text-zinc-100 border border-zinc-800 rounded-xl focus-within:ring-1 focus-within:ring-cyan-500/50 focus-within:border-cyan-500/50 transition-all font-mono text-xs overflow-hidden shadow-2xl"
      >
        <div className="flex items-center px-4 py-3">
          <svg className="w-4 h-4 text-zinc-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          <Command.Input 
            value={query}
            onValueChange={(val) => {
              setQuery(val);
              setOpen(true);
            }}
            placeholder={placeholder}
            className="bg-transparent border-none focus:outline-none w-full text-zinc-100 placeholder-zinc-600 font-bold"
          />
          {loading && (
            <div className="animate-spin h-4 w-4 border-2 border-cyan-500 border-t-transparent rounded-full ml-2"></div>
          )}
        </div>

        {open && results.length > 0 && (
          <Command.List 
            ref={parentRef}
            className="max-h-[300px] overflow-auto border-t border-zinc-800 p-2 scrollbar-thin scrollbar-thumb-zinc-700"
          >
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const player = results[virtualRow.index];
                const code = getCountryCode(player.country);
                
                return (
                  <Command.Item
                    key={player.player_id}
                    value={player.name}
                    onSelect={() => handleSelect(player)}
                    onClick={() => handleSelect(player)}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelect(player);
                    }}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="flex items-center px-3 py-2 rounded-lg cursor-pointer hover:bg-zinc-800/80 data-[selected=true]:bg-cyan-500/10 data-[selected=true]:text-cyan-400 transition-colors"
                  >
                    <div className="flex items-center gap-3 w-full">
                       <div className="w-5 flex-shrink-0">
                          {code && <Flag code={code.toUpperCase()} size="S" />}
                       </div>
                       <span className="font-bold truncate uppercase">{player.name}</span>
                       <span className="ml-auto text-[10px] text-zinc-600 font-mono">{player.country}</span>
                    </div>
                  </Command.Item>
                );
              })}
            </div>
          </Command.List>
        )}
      </Command>
    </div>
  );
}
