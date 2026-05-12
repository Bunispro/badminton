import React from 'react';

export function RetroGrid() {
  return (
    <div className="absolute inset-0 -z-10 opacity-20 pointer-events-none overflow-hidden">
      <div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#3f3f46_1px,transparent_1px),linear-gradient(to_bottom,#3f3f46_1px,transparent_1px)] bg-[size:40px_40px]"
        style={{
          maskImage: 'radial-gradient(ellipse at center, black, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black, transparent 70%)'
        }}
      />
    </div>
  );
}
