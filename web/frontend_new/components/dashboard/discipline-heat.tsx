'use client';

import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, LabelList, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import { API_BASE_URL } from '@/lib/api';

interface DurationData {
  label: string;
  value: number;
}

export function DisciplineHeatCard() {
  const [data, setData] = useState<DurationData[]>([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/dashboard/model-stats`)
      .then(res => res.json())
      .then(d => setData(d.durations || []))
      .catch(console.error);
  }, []);

  const outerData = data.map(item => ({
    name: item.label,
    value: item.value,
    fill: item.label.includes('S') ? '#3b82f6' : '#ec4899' // Sky Blue for Singles, Rose for Doubles
  }));

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-zinc-500 text-[10px] font-mono uppercase tracking-widest mb-2">Average Match Durations</h3>
      <div className="flex-grow min-h-[140px] mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={outerData} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
            <XAxis 
              dataKey="name" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#71717a', fontSize: 10, fontWeight: 'bold' }}
              interval={0}
            />
            <YAxis hide />
            <RechartsTooltip 
              cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              contentStyle={{ backgroundColor: '#18181b', border: 'none', borderRadius: '8px' }} 
              itemStyle={{ color: '#fff', fontSize: '10px' }} 
              formatter={(value: number) => [`${value} min`, 'Avg Duration']}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={32}>
              {outerData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} fillOpacity={0.8} />
              ))}
              <LabelList 
                dataKey="value" 
                position="top" 
                fill="#a1a1aa" 
                fontSize={10} 
                fontWeight="black"
                formatter={(val: number) => `${val.toFixed(0)}m`}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
