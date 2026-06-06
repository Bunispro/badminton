
export const getCountryCode = (countryName: string) => {
  if (!countryName) return null;
  const trimmed = countryName.trim();
  const codes: Record<string, string> = {
    "China": "CN", "Indonesia": "ID", "Japan": "JP", "Korea": "KR", "Thailand": "TH",
    "Denmark": "DK", "Chinese Taipei": "TW", "Malaysia": "MY", "India": "IN", "Spain": "ES",
    "Hong Kong": "HK", "Singapore": "SG", "Canada": "CA", "France": "FR", "England": "GB",
    "Vietnam": "VN", "USA": "US", "Scotland": "GB-SCT"
  };
  const code = codes[trimmed] || null;
  if (code === 'UK') return 'GB';
  if (code === 'uk') return 'gb';
  return code;
};

export const getBeamColors = (code: string) => {
  const mapping: Record<string, { from: string, middle?: string, to: string }> = {
    "CN": { from: "#ee1c25", middle: "#ffff00", to: "#ee1c25" },
    "ID": { from: "#ff0000", to: "#ffffff" },
    "JP": { from: "#ffffff", middle: "#bc002d", to: "#ffffff" },
    "KR": { from: "#ffffff", middle: "#0047a0", to: "#cd2e3a" },
    "TH": { from: "#a51931", middle: "#ffffff", to: "#2d2a4a" },
    "DK": { from: "#c60c30", to: "#ffffff" },
    "TW": { from: "#fe0000", middle: "#ffffff", to: "#000095" },
    "MY": { from: "#010066", middle: "#ffcc00", to: "#cc0001" },
    "IN": { from: "#ff9933", middle: "#ffffff", to: "#128807" },
    "ES": { from: "#aa151b", to: "#f1bf00" },
    "HK": { from: "#ee1c25", to: "#ffffff" },
    "SG": { from: "#ee1c25", to: "#ffffff" },
    "CA": { from: "#ff0000", to: "#ffffff" },
    "FR": { from: "#002395", middle: "#ffffff", to: "#ed2939" },
    "GB": { from: "#00247d", middle: "#ffffff", to: "#cf142b" },
    "VN": { from: "#da251d", to: "#ffff00" },
    "US": { from: "#b22234", middle: "#ffffff", to: "#3c3b6e" },
    "GB-SCT": { from: "#005eb8", to: "#ffffff" },
    "DEFAULT": { from: "#ffffff", to: "#a1a1aa" }
  };
  return mapping[code.toUpperCase()] || mapping["DEFAULT"];
};

export const formatScore = (score: string, isSide1: boolean) => {
  if (!score) return [];
  const sets = score.split(' ');
  return sets.map(set => {
    const parts = set.split('-');
    if (parts.length === 2) {
      return isSide1 ? `${parts[0]}-${parts[1]}` : `${parts[1]}-${parts[0]}`;
    }
    return set;
  });
};

export const getDominance = (score: string, isSide1: boolean) => {
  if (!score) return 0;
  const sets = score.split(' ');
  let totalDiff = 0;
  let setsCount = 0;
  for (const set of sets) {
    const parts = set.split('-');
    if (parts.length === 2) {
      const s1 = parseInt(parts[0]);
      const s2 = parseInt(parts[1]);
      if (!isNaN(s1) && !isNaN(s2)) {
        const diff = isSide1 ? (s1 - s2) : (s2 - s1);
        totalDiff += diff;
        setsCount++;
      }
    }
  }
  if (setsCount === 0) return 0;
  const avgDiff = totalDiff / setsCount;
  const dominance = 0.5 + (avgDiff / 42);
  return Math.min(Math.max(dominance, 0), 1);
};
