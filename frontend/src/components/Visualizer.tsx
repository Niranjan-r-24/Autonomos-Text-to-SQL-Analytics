'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { ChartConfig } from '@/types';

interface VisualizerProps {
  config?: ChartConfig | null;
  data?: Record<string, any>[];
  chartConfig?: ChartConfig | null;
  rows?: Record<string, any>[];
  columns?: string[];
}

const COLORS = [
  '#244E39', // Forest green
  '#3D8260', // Sage green
  '#2563EB', // Blue
  '#D97706', // Amber
  '#DC2626', // Red
  '#7C3AED', // Violet
  '#0D9488', // Teal
];

export function Visualizer({ config, data, chartConfig, rows }: VisualizerProps) {
  const [isClient, setIsClient] = React.useState(false);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const activeConfig = config || chartConfig;
  const rawData = data || rows || [];

  const activeData = React.useMemo(() => {
    if (!activeConfig || !rawData || rawData.length === 0) return [];
    return rawData.map((row) => {
      const clean: Record<string, any> = { ...row };
      for (const k of activeConfig.y_axis_keys || []) {
        const val = row[k];
        if (val !== undefined && val !== null) {
          const n = Number(val);
          clean[k] = isNaN(n) ? 0 : n;
        }
      }
      return clean;
    });
  }, [activeConfig, rawData]);

  if (!isClient) {
    return (
      <div className="h-72 w-full flex items-center justify-center text-stone-400 text-xs font-mono">
        Loading chart visualization...
      </div>
    );
  }

  if (!activeConfig) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-stone-400 text-xs font-sans space-y-1">
        <p className="font-medium text-stone-600">No chart recommended for this query result.</p>
        <p className="text-stone-400">This query (such as a single scalar value or raw record list) is best viewed in Table Results.</p>
      </div>
    );
  }

  if (!activeData || activeData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-stone-400 text-xs font-sans">
        No data available for visualization.
      </div>
    );
  }

  const { chart_type, x_axis_key, y_axis_keys, title } = activeConfig;

  if (!y_axis_keys || y_axis_keys.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-stone-400 text-xs font-sans">
        No metric values available to chart.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-stone-100">
        <h4 className="text-xs font-semibold text-stone-800 uppercase tracking-wider">{title}</h4>
        <span className="text-[11px] font-mono uppercase bg-sage-50 text-forest-700 px-2 py-0.5 rounded border border-sage-200/80 font-medium">
          {chart_type} chart
        </span>
      </div>

      <div className="h-72 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          {chart_type === 'line' ? (
            <LineChart data={activeData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F2" />
              <XAxis dataKey={x_axis_key} stroke="#9CA3AF" tick={{ fill: '#6B7280', fontSize: 11 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#6B7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E5E7EB',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                  fontSize: '12px',
                  color: '#1F2937',
                }}
                itemStyle={{ color: '#1F2937' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              {y_axis_keys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: COLORS[idx % COLORS.length] }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          ) : chart_type === 'pie' ? (
            <PieChart>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E5E7EB',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                  fontSize: '12px',
                  color: '#1F2937',
                }}
                itemStyle={{ color: '#1F2937' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Pie
                data={activeData}
                dataKey={y_axis_keys[0]}
                nameKey={x_axis_key}
                cx="50%"
                cy="50%"
                outerRadius={95}
                innerRadius={35}
                paddingAngle={2}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {activeData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={activeData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F2" />
              <XAxis dataKey={x_axis_key} stroke="#9CA3AF" tick={{ fill: '#6B7280', fontSize: 11 }} />
              <YAxis stroke="#9CA3AF" tick={{ fill: '#6B7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E5E7EB',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                  fontSize: '12px',
                  color: '#1F2937',
                }}
                itemStyle={{ color: '#1F2937' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              {y_axis_keys.map((key, idx) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={COLORS[idx % COLORS.length]}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={48}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
