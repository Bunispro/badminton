'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

export function HeaderSettings() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const model = searchParams.get('model') || 'elo';
  const hideForm = searchParams.get('hideForm') === 'true';

  const setModel = (val: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('model', val);
    router.push(`?${params.toString()}`);
    setOpen(false);
  };

  const setHideForm = (val: boolean) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('hideForm', val.toString());
    router.push(`?${params.toString()}`);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 transition-colors"
      >
        <svg className="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.173 1.246c1.59-.54 3.35 1.22 2.81 2.81a1.724 1.724 0 001.246 2.173c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.246 2.173c.54 1.59-1.22 3.35-2.81 2.81a1.724 1.724 0 00-2.173 1.246c-.426 1.756-2.924-1.756-3.35 0a1.724 1.724 0 00-2.173-1.246c-1.59.54-3.35-1.22-2.81-2.81a1.724 1.724 0 00-1.246-2.173c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.246-2.173c-.54-1.59 1.22-3.35 2.81-2.81A1.724 1.724 0 0010.325 4.317z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1 w-48 bg-zinc-900 border border-zinc-800 rounded-md shadow-lg z-50 p-3 space-y-3">
          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Model</div>
          <div className="flex gap-1.5">
            <button
              onClick={() => setModel('elo')}
              className={`flex-1 px-2.5 py-1.5 text-xs font-semibold rounded-md transition-all ${
                model === 'elo'
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
              }`}
            >
              ELO
            </button>
            <button
              onClick={() => setModel('whr')}
              className={`flex-1 px-2.5 py-1.5 text-xs font-semibold rounded-md transition-all ${
                model === 'whr'
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
              }`}
            >
              WHR
            </button>
            <button
              onClick={() => setModel('bwf')}
              className={`flex-1 px-2.5 py-1.5 text-xs font-semibold rounded-md transition-all ${
                model === 'bwf'
                  ? "bg-zinc-100 text-zinc-900 font-bold"
                  : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100"
              }`}
            >
              BWF
            </button>
          </div>

          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest pt-2 border-t border-zinc-800">Layout</div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400">Hide Form</span>
            <button
              onClick={() => setHideForm(!hideForm)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                hideForm ? "bg-cyan-500" : "bg-zinc-700"
              }`}
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  hideForm ? "translate-x-5" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between border-t border-zinc-800 pt-2">
            <span className="text-xs text-zinc-400">Model Info</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger><svg className="w-4 h-4 text-zinc-500 hover:text-zinc-300 cursor-pointer" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></TooltipTrigger>
                <TooltipContent className="bg-zinc-900 border-zinc-800 text-zinc-100 p-2 max-w-xs">
                  <p className="text-xs">
                    <strong>Current:</strong> Uses an Elo-based model for recent performance. <br />
                    <strong>All-Time:</strong> Uses WHR for a globally optimized historical view and adjusted ratings.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      )}
    </div>
  );
}
