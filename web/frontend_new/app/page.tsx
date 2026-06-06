'use client';

import React from 'react';
import { RetroGrid } from '@/components/magicui/retro-grid';
import { GiantSearch } from '@/components/giant-search';
import { BentoGrid, BentoCard } from '@/components/magicui/bento-grid';
import { 
  GlobalStatsCard, 
  ModelAccuracyCard, 
  DisciplineHeatCard, 
  TrendingPlayersCard, 
  LeaderboardPreviewCard, 
  MostSearchedCard, 
  UpsetAlertCard,
  EngineStatusCard
} from '@/components/bento-cards';

export default function Home() {
  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100 pb-20 overflow-x-hidden">
      {/* Background Pattern - Enhanced for the whole page */}
      <div className="fixed inset-0 pointer-events-none opacity-30">
        <RetroGrid />
      </div>
      
      {/* Hero Section */}
      <section className="pt-10 pb-8 px-4 relative z-30">
        <GiantSearch />
      </section>

      {/* Bento Grid Section - 3 Column Layout */}
      <section className="relative z-10 max-w-7xl mx-auto px-4">
        <BentoGrid className="md:grid-cols-3">
          {/* Main Content Area (Cols 1-2) */}
          <div className="md:col-span-2 md:row-span-2 overflow-hidden">
            <LeaderboardPreviewCard />
          </div>

          {/* Action Sidebar (Col 3) */}
          <BentoCard className="md:col-span-1 border-cyan-500/10">
            <GlobalStatsCard />
          </BentoCard>

          <BentoCard className="md:col-span-1 border-blue-500/10">
            <TrendingPlayersCard />
          </BentoCard>

          {/* Row 3 */}
          <BentoCard className="md:col-span-2 border-emerald-500/20 h-80">
            <ModelAccuracyCard />
          </BentoCard>

          <BentoCard className="md:col-span-1 h-80">
            <UpsetAlertCard />
          </BentoCard>

          {/* Row 4 */}
          <BentoCard className="md:col-span-1">
            <DisciplineHeatCard />
          </BentoCard>

          <BentoCard className="md:col-span-1 border-emerald-500/10">
            <EngineStatusCard />
          </BentoCard>

          <BentoCard className="md:col-span-1">
            <MostSearchedCard />
          </BentoCard>
        </BentoGrid>
      </section>

      <div className="fixed bottom-0 left-0 w-full h-32 bg-gradient-to-t from-black to-transparent pointer-events-none" />
    </div>
  );
}
