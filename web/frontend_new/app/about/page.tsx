'use client';

import { motion } from 'framer-motion';
import { RetroGrid } from '@/components/magicui/retro-grid';
import Link from 'next/link';

export default function AboutPage() {
  return (
    <div className="relative min-h-screen flex flex-col items-center justify-start py-20 px-4 bg-zinc-950 text-zinc-100 overflow-hidden">
      <RetroGrid />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-3xl w-full space-y-8 z-10"
      >
        <Link href="/" className="text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-2 mb-8">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
          Back to Home
        </Link>
        
        <h1 className="text-5xl font-bold tracking-tight">The Science of <span className="text-cyan-400">Badminton Pro</span></h1>
        
        <div className="space-y-6 text-zinc-400 leading-relaxed text-lg">
          <p>
            Badminton Pro is a state-of-the-art analytics platform designed to bring professional-grade statistics to the badminton community. 
            By leveraging advanced rating systems like <strong>ELO</strong> and <strong>Whole History Rating (WHR)</strong>, we provide a more accurate 
            representation of player skill than traditional ranking points.
          </p>
          
          <h2 className="text-2xl font-semibold text-zinc-100 mt-10">Our Rating Models</h2>
          <div className="grid md:grid-cols-2 gap-6 mt-4">
            <div className="bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
              <h3 className="text-cyan-400 font-bold mb-2">ELO Rating</h3>
              <p className="text-sm">A time-tested method for calculating relative skill levels. We use a modified K-factor optimized for badminton match intensity.</p>
            </div>
            <div className="bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
              <h3 className="text-cyan-400 font-bold mb-2">WHR (Whole History)</h3>
              <p className="text-sm">WHR analyzes a player&apos;s entire match history simultaneously to provide a smoother, more predictive rating over time.</p>
            </div>
          </div>
          
          <h2 className="text-2xl font-semibold text-zinc-100 mt-10">Why Analytics Matter?</h2>
          <p>
            In badminton, traditional rankings often favor players who attend more tournaments. Our models focus purely on performance, 
            accounting for opponent strength and match scores to reveal the true &quot;Pulse&quot; of the game.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
