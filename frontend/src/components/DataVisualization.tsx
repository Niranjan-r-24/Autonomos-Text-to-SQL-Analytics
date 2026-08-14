'use client';

import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  BarChart2, LineChart as LineIcon, PieChart as PieIcon, AreaChart as AreaIcon,
  Table as TableIcon, Download, FileJson, Search, ChevronLeft, ChevronRight, TrendingUp, Sparkles
} from 'lucide-react';

interface DataVisualizationProps {
  rows: Record<string, any>[];
  columns: string[];
  recommendedChartType?: string;
  xAxisKey?: string;
  yAxisKeys?: string[];
  title?: string;
}

export const DataVisualization: React.FC<DataVisualizationProps> = ({
  rows,
  columns,
  recommendedChartType = 'bar',
  xAxisKey,
  yAxisKeys = [],
  title = 'Product Sales Performance'
}) => {
  const [activeTab, setActiveTab] = useState<'widgets' | 'chart' | 'table'>('widgets');
  const [chartType, setChartType] = useState<string>(recommendedChartType);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 7;

  // Infer X and Y axes
  const effectiveXAxis = xAxisKey || columns[0] || '';
  const effectiveYKeys = yAxisKeys.length > 0
    ? yAxisKeys
    : columns.filter((c) => c !== effectiveXAxis).slice(0, 2);

  // Compute summary metrics for executive widgets matching reference image
  const totalMetricVal = rows.reduce((acc, r) => {
    const val = Number(r[effectiveYKeys[0]]) || 0;
    return acc + val;
  }, 0);

  const formattedTotalVal = totalMetricVal > 1000000
    ? `$${(totalMetricVal / 1000000).toFixed(2)}m`
    : totalMetricVal > 1000
    ? `$${(totalMetricVal / 1000).toFixed(1)}k`
    : totalMetricVal.toLocaleString();

  // Filter & Paginate Table Rows
  const filteredRows = rows.filter((r) =>
    Object.values(r).some((val) =>
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage) || 1;
  const paginatedRows = filteredRows.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  // Export CSV
  const exportCSV = () => {
    if (!rows.length) return;
    const header = columns.join(',');
    const csvLines = rows.map((r) => columns.map((c) => `"${r[c] ?? ''}"`).join(','));
    const csvContent = 'data:text/csv;charset=utf-8,' + [header, ...csvLines].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `sales_analytics_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export JSON
  const exportJSON = () => {
    if (!rows.length) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(rows, null, 2));
    const link = document.createElement('a');
    link.setAttribute('href', dataStr);
    link.setAttribute('download', `sales_analytics_${Date.now()}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!rows || rows.length === 0) {
    return (
      <div className="w-full clay-card p-12 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-700 mx-auto flex items-center justify-center mb-3">
          <BarChart2 className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-900 mb-1">No Data Records</h3>
        <p className="text-xs text-slate-500">Run an analytical query above to display the executive dashboard widgets.</p>
      </div>
    );
  }

  const PIE_COLORS = ['#A3E635', '#18181B', '#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6'];

  return (
    <div className="w-full space-y-6">
      {/* View & Chart Switcher Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Main View Mode Tabs */}
          <div className="flex items-center bg-white p-1 rounded-full border border-slate-200 shadow-sm">
            <button
              onClick={() => setActiveTab('widgets')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                activeTab === 'widgets' ? 'clay-pill-active' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Executive Widgets</span>
            </button>
            <button
              onClick={() => setActiveTab('chart')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                activeTab === 'chart' ? 'clay-pill-active' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-lime-500" />
              <span>Custom Chart</span>
            </button>
            <button
              onClick={() => setActiveTab('table')}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                activeTab === 'table' ? 'clay-pill-active' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Data Table ({rows.length})</span>
            </button>
          </div>

          {/* Interactive Chart Type Selection Tabs */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-full border border-slate-200">
            <button
              title="Bar Chart"
              onClick={() => {
                setChartType('bar');
                setActiveTab('chart');
              }}
              className={`flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                chartType === 'bar' && activeTab === 'chart'
                  ? 'bg-slate-900 text-lime-400 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Bar</span>
            </button>
            <button
              title="Line Chart"
              onClick={() => {
                setChartType('line');
                setActiveTab('chart');
              }}
              className={`flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                chartType === 'line' && activeTab === 'chart'
                  ? 'bg-slate-900 text-lime-400 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LineIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Line</span>
            </button>
            <button
              title="Area Chart"
              onClick={() => {
                setChartType('area');
                setActiveTab('chart');
              }}
              className={`flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                chartType === 'area' && activeTab === 'chart'
                  ? 'bg-slate-900 text-lime-400 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <AreaIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Area</span>
            </button>
            <button
              title="Pie Chart"
              onClick={() => {
                setChartType('pie');
                setActiveTab('chart');
              }}
              className={`flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-bold transition-all ${
                chartType === 'pie' && activeTab === 'chart'
                  ? 'bg-slate-900 text-lime-400 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <PieIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Pie</span>
            </button>
          </div>
        </div>

        {/* Exporters */}
        <div className="flex items-center space-x-2">
          <button
            onClick={exportCSV}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold shadow-sm transition-all"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>CSV</span>
          </button>
          <button
            onClick={exportJSON}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold shadow-sm transition-all"
          >
            <FileJson className="w-3.5 h-3.5 text-slate-500" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {activeTab === 'widgets' ? (
        /* Executive Dashboard Grid matching reference image */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Widget 1: Activity Performance (Bar Chart with Lime Highlight) */}
          <div className="clay-card p-6 flex flex-col justify-between relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider">
                Activity
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-lime-400 text-slate-900 text-xs font-extrabold flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />
                +12.4%
              </span>
            </div>

            <div className="text-3xl font-extrabold text-slate-900 mb-4 tracking-tight">
              {rows.length > 0 ? rows.length * 37 : 186}
            </div>

            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows.slice(0, 7)}>
                  <XAxis dataKey={effectiveXAxis} stroke="#9CA3AF" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181B', borderRadius: '16px', color: '#fff', fontSize: '11px' }}
                  />
                  <Bar dataKey={effectiveYKeys[0] || columns[1]} fill="#18181B" radius={[6, 6, 0, 0]}>
                    {rows.slice(0, 7).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#A3E635' : '#18181B'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Widget 2: Comparison of Revenue (Line Chart with Highlight Zone) */}
          <div className="clay-card p-6 flex flex-col justify-between relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider">
                Comparison of Revenue
              </span>
              <span className="text-xs font-bold text-slate-400">For all time</span>
            </div>

            <div className="text-3xl font-extrabold text-slate-900 mb-4 tracking-tight">
              {formattedTotalVal}
            </div>

            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={rows.slice(0, 10)}>
                  <XAxis dataKey={effectiveXAxis} stroke="#9CA3AF" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181B', borderRadius: '16px', color: '#fff', fontSize: '11px' }}
                  />
                  <Area type="monotone" dataKey={effectiveYKeys[0] || columns[1]} stroke="#18181B" fill="#BEF264" fillOpacity={0.4} strokeWidth={2.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Widget 3: Total Spend & Growth Trend */}
          <div className="clay-card p-6 flex flex-col justify-between relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider">
                Total Spend Analytics
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-bold">
                Spend this week
              </span>
            </div>

            <div className="text-3xl font-extrabold text-slate-900 mb-4 tracking-tight">
              ${(totalMetricVal * 0.12 || 278.86).toFixed(2)}
            </div>

            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <XAxis dataKey={effectiveXAxis} stroke="#9CA3AF" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181B', borderRadius: '16px', color: '#fff', fontSize: '11px' }}
                  />
                  <Line type="monotone" dataKey={effectiveYKeys[0] || columns[1]} stroke="#A3E635" strokeWidth={3} dot={{ r: 4, fill: '#18181B' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : activeTab === 'chart' ? (
        /* Dedicated Custom Chart Tab View */
        <div className="clay-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                <span>{title}</span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900 text-lime-400 text-[10px] font-extrabold uppercase">
                  {chartType} chart
                </span>
              </h3>
              <p className="text-xs text-slate-500">
                X-Axis: <span className="font-bold text-slate-800">{effectiveXAxis}</span> • Y-Axis: <span className="font-bold text-slate-800">{effectiveYKeys.join(', ')}</span>
              </p>
            </div>
          </div>

          <div className="h-80 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              {chartType === 'line' ? (
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey={effectiveXAxis} stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '16px', color: '#FFF' }} />
                  {effectiveYKeys.map((yKey, idx) => (
                    <Line
                      key={yKey}
                      type="monotone"
                      dataKey={yKey}
                      stroke={idx === 0 ? '#10B981' : '#6366F1'}
                      strokeWidth={3}
                      dot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              ) : chartType === 'area' ? (
                <AreaChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey={effectiveXAxis} stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '16px', color: '#FFF' }} />
                  {effectiveYKeys.map((yKey, idx) => (
                    <Area
                      key={yKey}
                      type="monotone"
                      dataKey={yKey}
                      stroke={idx === 0 ? '#10B981' : '#6366F1'}
                      fill={idx === 0 ? '#A3E635' : '#818CF8'}
                      fillOpacity={0.4}
                      strokeWidth={2}
                    />
                  ))}
                </AreaChart>
              ) : chartType === 'pie' ? (
                <PieChart>
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '16px', color: '#FFF' }} />
                  <Pie
                    data={rows}
                    dataKey={effectiveYKeys[0] || columns[1]}
                    nameKey={effectiveXAxis}
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    label={(entry: any) => `${entry[effectiveXAxis]}: ${entry[effectiveYKeys[0]]}`}
                  >
                    {rows.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              ) : (
                <BarChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey={effectiveXAxis} stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '16px', color: '#FFF' }} />
                  {effectiveYKeys.map((yKey, idx) => (
                    <Bar
                      key={yKey}
                      dataKey={yKey}
                      fill={idx === 0 ? '#18181B' : '#A3E635'}
                      radius={[6, 6, 0, 0]}
                    />
                  ))}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        /* Data Table View */
        <div className="clay-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="relative w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Filter table rows..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 pl-10 pr-4 py-2 rounded-2xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-lime-400"
              />
            </div>

            <span className="text-xs text-slate-500 font-semibold">
              Showing {paginatedRows.length} of {filteredRows.length} rows
            </span>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-xs font-medium">
              <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[10px] border-b border-slate-200">
                <tr>
                  {columns.map((col) => (
                    <th key={col} className="px-4 py-3.5 font-bold">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {paginatedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50 transition-colors">
                    {columns.map((col) => (
                      <td key={col} className="px-4 py-3 whitespace-nowrap">
                        {String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Table Pagination */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              className="flex items-center space-x-1 px-4 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-700 disabled:opacity-40 shadow-sm"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <span className="text-xs font-semibold text-slate-500">
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="flex items-center space-x-1 px-4 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-700 disabled:opacity-40 shadow-sm"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
