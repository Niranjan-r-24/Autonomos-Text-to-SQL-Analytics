'use client';

import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  BarChart2, LineChart as LineIcon, PieChart as PieIcon, AreaChart as AreaIcon,
  Table as TableIcon, Download, FileJson, Search, ChevronLeft, ChevronRight, Clock, Hash
} from 'lucide-react';

interface DataVisualizationProps {
  rows: Record<string, any>[];
  columns: string[];
  recommendedChartType?: string;
  xAxisKey?: string;
  yAxisKeys?: string[];
  title?: string;
  executionTimeSec?: number;
  sqlExecutionTimeMs?: number;
}

export const DataVisualization: React.FC<DataVisualizationProps> = ({
  rows,
  columns,
  recommendedChartType = 'bar',
  xAxisKey,
  yAxisKeys = [],
  title = 'Query Results',
  executionTimeSec,
  sqlExecutionTimeMs,
}) => {
  const [activeTab, setActiveTab] = useState<'table' | 'chart'>('table');
  const [chartType, setChartType] = useState<string>(recommendedChartType || 'bar');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;

  // Infer X and Y axes
  const effectiveXAxis = xAxisKey || columns[0] || '';
  const effectiveYKeys = yAxisKeys.length > 0
    ? yAxisKeys
    : columns.filter((c) => c !== effectiveXAxis).slice(0, 2);

  // Filter & Paginate Table Rows
  const filteredRows = rows.filter((r) =>
    Object.values(r).some((val) =>
      String(val ?? '').toLowerCase().includes(searchTerm.toLowerCase())
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
    link.setAttribute('download', `query_results_${Date.now()}.csv`);
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
    link.setAttribute('download', `query_results_${Date.now()}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!rows || rows.length === 0) {
    return (
      <div className="w-full clay-card p-10 bg-white border border-slate-200 text-center space-y-2">
        <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-500 mx-auto flex items-center justify-center">
          <TableIcon className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-900">No Records Returned</h3>
        <p className="text-xs text-slate-500">The query executed successfully but produced zero matching rows.</p>
      </div>
    );
  }

  const PIE_COLORS = ['#A3E635', '#18181B', '#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6'];

  return (
    <div className="w-full clay-card p-6 bg-white border border-slate-200 shadow-sm space-y-5">
      {/* Top Header: View Tabs, Execution Stats, and Exporters */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-100">
        <div className="flex flex-wrap items-center gap-2">
          {/* Main View Mode Tabs */}
          <div className="flex items-center bg-slate-100 p-1 rounded-full border border-slate-200">
            <button
              onClick={() => setActiveTab('table')}
              className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                activeTab === 'table' ? 'clay-pill-active' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Data Table ({rows.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('chart')}
              className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                activeTab === 'chart' ? 'clay-pill-active' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Visual Chart</span>
            </button>
          </div>

          {/* Chart Type Selector when in Chart View */}
          {activeTab === 'chart' && (
            <div className="flex items-center space-x-1 bg-slate-50 p-1 rounded-full border border-slate-200">
              <button
                onClick={() => setChartType('bar')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  chartType === 'bar' ? 'bg-slate-900 text-lime-400 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Bar
              </button>
              <button
                onClick={() => setChartType('line')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  chartType === 'line' ? 'bg-slate-900 text-lime-400 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Line
              </button>
              <button
                onClick={() => setChartType('area')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  chartType === 'area' ? 'bg-slate-900 text-lime-400 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Area
              </button>
              <button
                onClick={() => setChartType('pie')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  chartType === 'pie' ? 'bg-slate-900 text-lime-400 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Pie
              </button>
            </div>
          )}
        </div>

        {/* Execution Metrics & Exporters */}
        <div className="flex items-center space-x-2">
          {sqlExecutionTimeMs !== undefined && (
            <span className="hidden sm:flex items-center space-x-1 px-3 py-1 rounded-full bg-slate-50 text-slate-600 text-xs font-medium border border-slate-200">
              <Clock className="w-3 h-3 text-slate-400" />
              <span>{sqlExecutionTimeMs} ms</span>
            </span>
          )}

          <button
            onClick={exportCSV}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold shadow-sm transition-all"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>CSV</span>
          </button>
          <button
            onClick={exportJSON}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold shadow-sm transition-all"
          >
            <FileJson className="w-3.5 h-3.5 text-slate-500" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {activeTab === 'table' ? (
        /* Data Table View */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="relative w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-2.5" />
              <input
                type="text"
                placeholder="Filter table rows..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-200 pl-10 pr-4 py-1.5 rounded-2xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-lime-400"
              />
            </div>

            <span className="text-xs text-slate-500 font-semibold">
              Showing {paginatedRows.length} of {filteredRows.length} rows ({columns.length} columns)
            </span>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-xs font-medium">
              <thead className="bg-slate-50 text-slate-700 uppercase tracking-wider text-[10px] border-b border-slate-200 font-bold">
                <tr>
                  {columns.map((col) => (
                    <th key={col} className="px-4 py-3">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {paginatedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/80 transition-colors">
                    {columns.map((col) => (
                      <td key={col} className="px-4 py-2.5 whitespace-nowrap">
                        {String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Table Pagination */}
          {totalPages > 1 && (
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
          )}
        </div>
      ) : (
        /* Visual Chart View */
        <div className="space-y-3">
          <div className="text-xs text-slate-500">
            Dimension: <strong className="text-slate-800">{effectiveXAxis}</strong>
            {effectiveYKeys.length > 0 && (
              <> • Metrics: <strong className="text-slate-800">{effectiveYKeys.join(', ')}</strong></>
            )}
          </div>

          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              {chartType === 'line' ? (
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey={effectiveXAxis} stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#FFF', fontSize: '11px' }} />
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
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#FFF', fontSize: '11px' }} />
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
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#FFF', fontSize: '11px' }} />
                  <Pie
                    data={rows}
                    dataKey={effectiveYKeys[0] || columns[1]}
                    nameKey={effectiveXAxis}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(entry: any) => `${entry[effectiveXAxis]}: ${entry[effectiveYKeys[0]]}`}
                  >
                    {rows.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              ) : (
                <BarChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey={effectiveXAxis} stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#FFF', fontSize: '11px' }} />
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
      )}
    </div>
  );
};
