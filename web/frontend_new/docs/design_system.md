# Phantom Theme Design System

This document outlines the design system, colors, and components for the Badminton App frontend ("Phantom" theme), established in May 2026. Future agents should adhere to these guidelines to maintain consistency.

## Core Theme: "Phantom"

- **Main Background**: `bg-zinc-950` (`#09090b`)
- **Card Background**: `bg-zinc-900` (`#18181b`)
- **Borders**: `border-zinc-800`
- **Accents**: `text-cyan-400`
- **Numbers**: 
  - Main numbers: `text-zinc-100` with `font-mono`
  - Lesser numbers (uncertainty, graph axis): `text-zinc-500`
- **Status Colors**:
  - Increase/Positive: `text-emerald-500`
  - Decrease/Negative: `text-rose-500`
  - Uncertainty: `text-zinc-500`

## Components

### 1. The "Phantom" Primary Button
```html
<button class="px-4 py-2 bg-zinc-100 text-zinc-900 hover:bg-zinc-300 shadow-[0_0_15px_rgba(255,255,255,0.1)] transition-all font-semibold rounded-lg">
  Action
</button>
```

### 2. Custom Magic UI Components
Located in `@/components/magicui/`:
- **Shiny Button**: Button with a moving shine effect on hover.
- **Number Ticker**: Animates numbers counting up.
- **Border Beam**: Moving glow effect around the border of a card.
- **Retro Grid**: Subtle background grid pattern (opacity 20%, zinc-700).
- **Animated Beam**: Shows data flow between nodes.
- **Bento Grid**: Layout system for cards.

## Library Specifics

### 1. Tremor / Recharts Graphs
- **Trend Line**: `stroke-sky-400`
- **Area Fill**: `fill-sky-400/5` (Solid color with low opacity, not a heavy gradient).
- **Axis Labels**: `zinc-500` (`#71717a`), `font-mono text-[10px] uppercase tracking-wider`.
- **Grid Lines**: `zinc-800/50` (barely visible).
- **Tooltip**: `bg-zinc-900 border-zinc-800`.

To apply these to Tremor/Recharts, use the following CSS overrides in your page or global CSS:
```css
.recharts-cartesian-axis-tick-value {
  font-family: monospace !important;
  font-size: 10px !important;
  fill: #71717a !important;
}
.recharts-cartesian-grid-horizontal line,
.recharts-cartesian-grid-vertical line {
  stroke: rgba(39, 39, 42, 0.5) !important;
}
.recharts-area-curve {
  stroke: #38bdf8 !important;
}
.recharts-area-area {
  stroke: none !important;
  fill: #38bdf8 !important;
  fill-opacity: 0.05 !important;
}
```

### 2. Flags (Flagpack)
To keep flags from being too loud in dark mode:
```html
<div class="grayscale-[0.1] brightness-[0.9] rounded-sm opacity-90 hover:grayscale-0 hover:opacity-100 transition-all">
  <Flag code="US" size="S" />
</div>
```

### 3. Icons (Hugeicons)
- Use the `@hugeicons/react` package.
- Style: Stroke Rounded.
- Rule: Keep stroke width at `1.5px` for a pro look.

## Leaderboard Table (TanStack Style)
- **Sticky Columns**: Use `sticky left-0` on Rank and Player Name columns.
- **Row Hover**: Use `hover:bg-zinc-800/30` or similar subtle glow.
- **Sparklines**: Add a tiny 100px wide SVG line graph next to ELO to show form.
