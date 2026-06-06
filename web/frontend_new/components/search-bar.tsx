'use client';

import { useState, useEffect, useRef } from 'react';
import { Command } from 'cmdk';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useRouter } from 'next/navigation';
import Flag from 'react-flagpack';
import 'react-flagpack/dist/style.css';
import countryCodes from '@/lib/countryCodes.json';
import React from 'react';
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

export function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 2) {
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
    }, 300); // 300ms debounce

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

  const onSelect = (id: string) => {
    setOpen(false);
    setQuery('');
    router.push(`/player/${id}`);
  };

  const rowVirtualizer = useVirtualizer({
    count: results.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 5,
  });

  return (
    <div className="relative w-[400px]" ref={containerRef}>
      <Command 
        shouldFilter={false} 
        className="bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-md focus-within:ring-1 focus-within:ring-sky-500/50 focus-within:border-sky-500/50 transition-all font-mono text-xs"
      >
        <div className="flex items-center px-3 py-2">
          <svg className="w-3.5 h-3.5 text-zinc-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          <Command.Input 
            value={query}
            onValueChange={(val) => {
              setQuery(val);
              setOpen(true);
              if (val.length < 2) {
                setResults([]);
              }
            }}
            placeholder="Search players"
            className="bg-transparent border-none focus:outline-none w-full text-zinc-100 placeholder-zinc-500"
          />
          {loading && (
            <div className="animate-spin h-3.5 w-3.5 border-2 border-zinc-500 border-t-transparent rounded-full ml-2"></div>
          )}
        </div>

        {open && results.length > 0 && (
          <Command.List 
            ref={parentRef} 
            className="absolute top-full left-0 w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-md shadow-lg z-50 max-h-60 overflow-auto"
          >
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const item = results[virtualRow.index];
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
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="flex items-center justify-between px-3 py-2 hover:bg-zinc-800 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {countryCode && (
                        <div className="grayscale-[0.1] brightness-[0.9] rounded-sm opacity-90 scale-75 origin-left">
                          <Flag code={countryCode.toUpperCase()} size="S" />
                        </div>
                      )}
                      <span className="font-semibold text-zinc-100 truncate">{item.name}</span>
                    </div>
                    {item.rating && (
                      <span className="text-zinc-500 text-xs font-mono ml-2">
                        {Math.round(item.rating)}
                      </span>
                    )}
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
