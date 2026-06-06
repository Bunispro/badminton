import React from 'react';

interface FlagProps {
  code: string;
  className?: string;
  width?: string;
  size?: string; // Kept for backward compatibility if needed
}

export const Flag = React.memo(({ code, className = "", width = "w80" }: FlagProps) => {
  if (!code) return null;
  const lowerCode = code.toLowerCase();
  return (
    <img 
      src={`https://flagcdn.com/${width}/${lowerCode}.png`} 
      alt={code}
      className={`inline-block object-cover ${className}`}
      onError={(e) => {
        (e.target as HTMLImageElement).src = `https://flagcdn.com/${width}/un.png`;
      }}
    />
  );
});
Flag.displayName = 'Flag';
