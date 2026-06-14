import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Participant {
  id: string;
  name: string;
  country?: string;
}

interface Match {
  match_id: string;
  date: string;
  event: string;
  model: string;
  winner_side: number;
  side1: Participant[];
  side2: Participant[];
  score?: string;
  tournament?: string;
  duration?: number;
  side1_rating?: number;
  side2_rating?: number;
  predicted_prob?: number;
  actual?: number;
  predicted_win_rate?: number;
  round?: string;
}

interface HistoryPoint {
  date: string;
  rating: number;
  rank?: number;
  timestamp?: number;
}

interface RatingGraphProps {
  chartData: HistoryPoint[];
  isSharpView: boolean;
  matches?: Match[];
  history: HistoryPoint[];
  id: string;
  model: string;
}

interface CustomDotProps {
  cx: number;
  cy: number;
  payload: {
    date: string;
    rating: number;
    rank?: number;
  };
  isPeak?: boolean;
  isSmallDot?: boolean;
  color?: string;
  r?: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: {
    payload: {
      date: string;
      rating: number;
      rank?: number;
    };
  }[];
}

export const RatingGraph = React.memo(({ chartData, isSharpView, matches, history, id, model }: RatingGraphProps) => {
  const CustomDot = (props: CustomDotProps) => {
    const { cx, cy, payload, isPeak, isSmallDot, color: originalColor, r: originalR } = props;
    
    // Find if a match was played on this date
    const match = matches ? matches.find((m: Match) => m.date === payload.date) : null;
    
    // Determine color and radius
    let isMatchDot = false;
    let dotColor = originalColor || "#38bdf8";
    let dotRadius = originalR || 4;
    let won = false;
    
    if (isPeak) {
      dotColor = "#38bdf8"; // Peak dot is ALWAYS a unique premium sky blue
      dotRadius = 6.5; // stand out prominently
    } else if (isSmallDot && match && model !== 'bwf') {
      isMatchDot = true;
      const isPlayerInSide1 = match.side1?.some((p: Participant) => p.id === id);
      won = (isPlayerInSide1 && match.winner_side === 1) || (!isPlayerInSide1 && match.winner_side === 2);
      dotColor = won ? "#10b981" : "#ef4444"; // Emerald green for win, Rose red for loss
      dotRadius = 4.5; // Slightly shrunk size for match dots
    }
    
    // If it's sharp view and neither peak nor match dot, hide it to keep the line clean
    if (isSmallDot && !isMatchDot && !isPeak) return null;
    
    // Otherwise, if not sharp view and not peak, hide
    if (!isSmallDot && !isPeak) return null;

    const dotId = `${payload.date}-${Math.round(payload.rating)}-${Math.round(cx)}-${Math.round(cy)}`;
    let hash = 0;
    for (let i = 0; i < dotId.length; i++) {
      hash = (hash << 5) - hash + dotId.charCodeAt(i);
      hash |= 0;
    }
    const positiveHash = Math.abs(hash);
    const delay = (positiveHash % 4000) / 1000;
    const duration = 2.2 + (positiveHash % 1600) / 1000;

    return (
      <g key={`dot-${payload.date}-${cx}-${cy}`}>
        {/* Fill dot */}
        <circle cx={cx} cy={cy} r={dotRadius} fill={dotColor} stroke="#18181b" strokeWidth={1.5} />
        
        {/* Pulsing Ripple outer circle for match dots and peak dot */}
        {(isMatchDot || isPeak) && (
          <circle cx={cx} cy={cy} r={dotRadius} fill="none" stroke={dotColor} strokeWidth={1.5}
            style={{
              animation: `ripple ${duration}s infinite linear`,
              animationDelay: `${delay}s`,
              transformOrigin: `${cx}px ${cy}px`,
            }}
          />
        )}
        
        {/* Peak rating overlay */}
        {isPeak && (
          <g>
            <text x={cx} y={cy - 16} fill="#f4f4f5" fontSize={16} fontWeight="bold" opacity={0.9} textAnchor="middle" fontFamily="monospace">
              {model === 'bwf' ? `#${payload.rank}` : Math.round(payload.rating)}
            </text>
            <text x={cx} y={cy - 36} fill="#71717a" fontSize={13} opacity={0.7} textAnchor="middle" fontFamily="monospace">
              {model === 'bwf' ? 'Peak BWF Rank' : new Date(payload.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
            </text>
          </g>
        )}
      </g>
    );
  };

  const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const historyIndex = history.findIndex((h: HistoryPoint) => h.date === data.date);
      const prevRating = historyIndex > 0 ? history[historyIndex - 1].rating : null;
      const ratingChange = prevRating ? data.rating - prevRating : null;
      const match = isSharpView && matches ? matches.find((m: Match) => m.date === data.date) : null;
      
      if (match) {
        const isPlayerInSide1 = match.side1?.some((p: Participant) => p.id === id);
        const playerSide = isPlayerInSide1 ? match.side1 : match.side2;
        const opponentSide = isPlayerInSide1 ? match.side2 : match.side1;
        let displayScore = match.score;
        if (!isPlayerInSide1 && match.score) {
          displayScore = match.score.split(' ').map((set: string) => {
            const parts = set.split('-');
            return parts.length === 2 ? `${parts[1]}-${parts[0]}` : set;
          }).join(' ');
        }

        return (
          <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 text-xs shadow-xl backdrop-blur-sm max-w-xs">
            <div className="text-zinc-400 font-mono mb-1 flex justify-between">
              <span>{new Date(data.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
              {match.duration && (
                <span className="flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                  {match.duration}m
                </span>
              )}
            </div>
            <div className="flex flex-col gap-0.5 mb-2">
              {model === 'bwf' ? (
                <>
                  <span className="text-sky-400 font-bold text-sm">BWF Rank: #{data.rank}</span>
                  <span className="text-zinc-300 text-xs">Points: {data.rating.toLocaleString()}</span>
                </>
              ) : (
                <div className="flex justify-between items-baseline gap-4 mb-2">
                  <span className="text-zinc-100 font-bold text-sm">Rating: {Math.round(data.rating)}</span>
                  {ratingChange !== null && (
                    <span className={`text-xs font-bold ${ratingChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {ratingChange >= 0 ? '+' : ''}{Math.round(ratingChange)}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="text-zinc-400 text-xs">
              {match.tournament && (
                <div className="mb-1 text-zinc-300 font-semibold truncate"><span className="text-zinc-500">Event:</span> {match.tournament}</div>
              )}
              {(playerSide?.length > 1 || opponentSide?.length > 1) ? (
                <>
                  <div className="mb-0.5"><span className="text-zinc-500">Side 1:</span> {playerSide?.map((p: Participant) => p.name).join(' / ') || 'Unknown'}</div>
                  <div className="mb-1"><span className="text-zinc-500">Side 2:</span> {opponentSide?.map((p: Participant) => p.name).join(' / ') || 'Unknown'}</div>
                </>
              ) : (
                <div className="mb-1"><span className="text-zinc-500">Vs:</span> {opponentSide?.map((p: Participant) => p.name).join(' / ') || 'Unknown'}</div>
              )}
              <div><span className="text-zinc-500">Score:</span> <span className="font-mono text-sky-400">{displayScore}</span></div>
            </div>
          </div>
        );
      }

      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 text-xs shadow-xl backdrop-blur-sm max-w-xs">
          <div className="text-zinc-400 font-mono mb-1">
            {new Date(data.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
          </div>
          <div className="flex flex-col gap-0.5">
            {model === 'bwf' ? (
              <>
                <span className="text-sky-400 font-bold text-sm">BWF Rank: #{data.rank}</span>
                <span className="text-zinc-300 text-xs">Points: {data.rating.toLocaleString()}</span>
              </>
            ) : (
              <span className="text-zinc-100 font-bold text-sm">Rating: {Math.round(data.rating)}</span>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-64 w-full">
      <style>{`
        @keyframes ripple {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(3); opacity: 0; }
        }
      `}</style>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 40, right: 40, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="colorRating" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="timestamp" 
            type="number"
            domain={['dataMin', 'dataMax']}
            stroke="#71717a" 
            tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#71717a' }}
            tickCount={6}
            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
          />
          <YAxis domain={['dataMin - 100', 'dataMax + 100']} hide={true} />
          <Tooltip content={<CustomTooltip />} />
          <Area 
            type={isSharpView ? "linear" : "monotone"} 
            dataKey="rating" 
            stroke="#38bdf8" 
            fillOpacity={1} 
            fill="url(#colorRating)"
            isAnimationActive={false}
            dot={(props: { cx: number; cy: number; payload: { date: string; rating: number; rank?: number; color?: string; r?: number; isPeak?: boolean }; key?: string }) => {
              const { key, ...rest } = props;
              const { color, r, isPeak } = props.payload;
              return <CustomDot key={key} {...rest} isPeak={isPeak} isSmallDot={isSharpView} color={color} r={r} />;
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
});

RatingGraph.displayName = 'RatingGraph';
