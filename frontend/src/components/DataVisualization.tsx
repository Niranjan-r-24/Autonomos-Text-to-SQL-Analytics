'use client';

import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  BarChart2, LineChart as LineIcon, PieChart as PieIcon, AreaChart as AreaIcon,
  Table as TableIcon, Download, FileJson, Search, ChevronLeft, ChevronRight, Clock, Hash,
  ArrowUpDown, ArrowUp, ArrowDown
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

const PIE_COLORS = ['#10B981', '#059669', '#34D399', '#047857', '#0284C7', '#F59E0B', '#8B5CF6'];

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
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Infer X and Y axes
  const effectiveXAxis = xAxisKey || columns[0] || '';
  const effectiveYKeys = yAxisKeys.length > 0
    ? yAxisKeys
    : columns.filter((c) => c !== effectiveXAxis).slice(0, 2);

  // Filter & Sort Table Rows
  const filteredAndSortedRows = React.useMemo(() => {
    let list = [...rows];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((r) =>
        columns.some((c) => String(r[c] ?? '').toLowerCase().includes(q))
      );
    }
    if (sortColumn) {
      list.sort((a, b) => {
        const valA = a[sortColumn];
        const valB = b[sortColumn];
        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortDirection === 'asc' ? valA - valB : valB - valA;
        }
        const strA = String(valA ?? '').toLowerCase();
        const strB = String(valB ?? '').toLowerCase();
        if (strA < strB) return sortDirection === 'asc' ? -1 : 1;
        if (strA > strB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return list;
  }, [rows, columns, searchTerm, sortColumn, sortDirection]);

  const totalPages = Math.ceil(filteredAndSortedRows.length / rowsPerPage) || 1;
  const paginatedRows = filteredAndSortedRows.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  const handleSort = (colKey: string) => {
    if (sortColumn === colKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(colKey);
      setSortDirection('asc');
    }
  };

  // Export CSV
  const exportCSV = () => {
    if (!rows.length) return;
    const header = columns.join(',');
    const csvLines = rows.map((r) => columns.map((c) => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(','));
    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [header, ...csvLines].join('\n');
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
      <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] p-10 rounded-2xl text-center space-y-2 shadow-2xs">
        <div className="w-10 h-10 rounded-xl bg-[#F8FAFC] text-[#64748B] mx-auto flex items-center justify-center">
          <TableIcon className="w-5 h-5 text-[#94A3B8]" />
        </div>
        <h3 className="text-sm font-bold text-[#0F172A]">No Records Returned</h3>
        <p className="text-xs text-[#64748B]">The query executed successfully but produced zero matching rows.</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981]/40 rounded-2xl p-5 sm:p-6 shadow-2xs space-y-4 transition-all">
      {/* Top Header: View Tabs, Execution Stats, and Exporters */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
        <div className="flex flex-wrap items-center gap-2">
          {/* Main View Mode Tabs */}
          <div className="flex items-center bg-[#F8FAFC] p-1 rounded-xl border border-[#E2E8F0]">
            <button
              onClick={() => setActiveTab('table')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'table' ? 'bg-[#10B981] text-white shadow-2xs' : 'text-[#475569] hover:text-[#0F172A]'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Data Table ({rows.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('chart')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'chart' ? 'bg-[#10B981] text-white shadow-2xs' : 'text-[#475569] hover:text-[#0F172A]'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Visual Chart</span>
            </button>
          </div>

          {/* Chart Type Selector when in Chart View */}
          {activeTab === 'chart' && (
            <div className="flex items-center space-x-1 bg-[#F8FAFC] p-1 rounded-xl border border-[#E2E8F0]">
              {(['bar', 'line', 'area', 'pie'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setChartType(t)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold uppercase text-[10px] transition-all cursor-pointer ${
                    chartType === t ? 'bg-[#0F172A] text-white shadow-2xs' : 'text-[#64748B] hover:text-[#0F172A]'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Tools: Exporters & Timing */}
        <div className="flex items-center space-x-2">
          {(sqlExecutionTimeMs !== undefined || executionTimeSec !== undefined) && (
            <div className="flex items-center space-x-1 text-[11px] text-[#64748B] bg-[#F8FAFC] border border-[#E2E8F0] px-2.5 py-1 rounded-lg font-mono">
              <Clock className="w-3 h-3 text-[#10B981]" />
              <span>{sqlExecutionTimeMs !== undefined ? `${sqlExecutionTimeMs}ms` : `${executionTimeSec}s`}</span>
            </div>
          )}

          <button
            onClick={exportCSV}
            className="flex items-center space-x-1 px-3 py-1 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] text-xs font-semibold text-[#0F172A] transition-colors cursor-pointer"
            title="Download CSV"
          >
            <Download className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">CSV</span>
          </button>

          <button
            onClick={exportJSON}
            className="flex items-center space-x-1 px-3 py-1 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] text-xs font-semibold text-[#0F172A] transition-colors cursor-pointer"
            title="Download JSON"
          >
            <FileJson className="w-3.5 h-3.5 text-[#D97706]" />
            <span className="hidden sm:inline">JSON</span>
          </button>
        </div>
      </div>

      {/* View Content */}
      {activeTab === 'table' ? (
        <div className="space-y-3">
          {/* Table Search */}
          <div className="flex items-center justify-between gap-2">
            <div className="relative flex-1 max-w-xs">
              <Search className="w-3.5 h-3.5 text-[#10B981] absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Search table rows..."
                className="w-full bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl pl-8 pr-3 py-1.5 text-xs text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#10B981]"
              />
            </div>

            <div className="flex items-center gap-2 text-xs text-[#64748B]">
              <span className="font-mono text-[11px] text-[#047857]">
                Total: {filteredAndSortedRows.length} rows
              </span>
              <select
                value={rowsPerPage}
                onChange={(e) => {
                  setRowsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-[#FFFFFF] border border-[#CBD5E1] rounded px-2 py-0.5 text-[11px] text-[#0F172A] focus:outline-none"
              >
                <option value={5}>5 per page</option>
                <option value={10}>10 per page</option>
                <option value={25}>25 per page</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl bg-[#FFFFFF] custom-scrollbar shadow-2xs">
            <table className="w-full text-xs text-left text-[#0F172A] border-collapse">
              <thead className="bg-[#F8FAFC] text-[#047857] uppercase font-semibold border-b border-[#E2E8F0]">
                <tr>
                  <th className="p-2.5 text-[10px] w-8">#</th>
                  {columns.map((c) => (
                    <th
                      key={c}
                      onClick={() => handleSort(c)}
                      className="p-2.5 cursor-pointer hover:text-[#0F172A] transition-colors select-none"
                    >
                      <div className="flex items-center gap-1 font-mono text-[11px]">
                        <span>{c}</span>
                        {sortColumn === c ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="w-3 h-3 text-[#10B981]" />
                          ) : (
                            <ArrowDown className="w-3 h-3 text-[#10B981]" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-[#94A3B8] opacity-60" />
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0] font-mono text-[11px]">
                {paginatedRows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} className="p-6 text-center text-[#94A3B8] font-sans">
                      No matching records found.
                    </td>
                  </tr>
                ) : (
                  paginatedRows.map((r, rIdx) => (
                    <tr key={rIdx} className="hover:bg-[#F1F5F9] transition-colors">
                      <td className="p-2.5 text-[10px] text-[#64748B]">
                        {(currentPage - 1) * rowsPerPage + rIdx + 1}
                      </td>
                      {columns.map((c) => (
                        <td key={c} className="p-2.5 text-[#0F172A] max-w-xs truncate">
                          {String(r[c] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-1 text-xs text-[#047857]">
              <span className="text-[11px] font-mono">
                Page {currentPage} of {totalPages}
              </span>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] rounded-lg disabled:opacity-40 text-[#047857] cursor-pointer"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] rounded-lg disabled:opacity-40 text-[#047857] cursor-pointer"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Chart View */
        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height={260}>
            {chartType === 'bar' ? (
              <BarChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey={effectiveXAxis} stroke="#475569" fontSize={11} />
                <YAxis stroke="#475569" fontSize={11} />
                <Tooltip
                  cursor={{ fill: 'rgba(16, 185, 129, 0.08)' }}
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#10B981',
                    color: '#0F172A',
                    borderRadius: '10px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                {effectiveYKeys.map((yKey, idx) => (
                  <Bar
                    key={yKey}
                    dataKey={yKey}
                    fill={PIE_COLORS[idx % PIE_COLORS.length]}
                    radius={[6, 6, 0, 0]}
                  />
                ))}
              </BarChart>
            ) : chartType === 'line' ? (
              <LineChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey={effectiveXAxis} stroke="#475569" fontSize={11} />
                <YAxis stroke="#475569" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#10B981',
                    color: '#0F172A',
                    borderRadius: '10px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                {effectiveYKeys.map((yKey, idx) => (
                  <Line
                    key={yKey}
                    type="monotone"
                    dataKey={yKey}
                    stroke={PIE_COLORS[idx % PIE_COLORS.length]}
                    strokeWidth={3}
                    dot={{ r: 4 }}
                  />
                ))}
              </LineChart>
            ) : chartType === 'area' ? (
              <AreaChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey={effectiveXAxis} stroke="#475569" fontSize={11} />
                <YAxis stroke="#475569" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#10B981',
                    color: '#0F172A',
                    borderRadius: '10px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                {effectiveYKeys.map((yKey, idx) => (
                  <Area
                    key={yKey}
                    type="monotone"
                    dataKey={yKey}
                    stroke={PIE_COLORS[idx % PIE_COLORS.length]}
                    fill={PIE_COLORS[idx % PIE_COLORS.length]}
                    fillOpacity={0.25}
                  />
                ))}
              </AreaChart>
            ) : (
              <PieChart>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#10B981',
                    color: '#0F172A',
                    borderRadius: '10px',
                    fontSize: '11px',
                  }}
                />
                <Legend />
                <Pie
                  data={rows}
                  dataKey={effectiveYKeys[0] || columns[1] || columns[0]}
                  nameKey={effectiveXAxis}
                  cx="50%"
                  cy="50%"
                  outerRadius={85}
                  label={({ name, percent }: any) =>
                    `${name ? String(name).slice(0, 12) : ''}: ${(((percent as number) || 0) * 100).toFixed(0)}%`
                  }
                >
                  {rows.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
