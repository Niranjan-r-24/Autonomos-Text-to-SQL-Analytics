'use client';

import React, { useState, useMemo } from 'react';
import {
  HelpCircle, Code2, Check, Copy, ShieldCheck, Sparkles, Clock, Edit3, Play,
  FileText, Download, Search, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight,
  TrendingUp, Database, Table as TableIcon, BarChart2, PieChart as PieIcon, LineChart as LineIcon,
  AreaChart as AreaIcon, RotateCcw, X, Layers
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface QueryResponseCardProps {
  question: string;
  sql: string;
  explanation: string;
  generatedBy?: string;
  rows: Record<string, any>[];
  columns: string[];
  rowCount?: number;
  executionTimeSec?: number;
  sqlExecutionTimeMs?: number;
  visualization?: {
    chart_type?: string;
    x_axis?: string;
    y_axes?: string[];
    title?: string;
  };
  onRunCustomSql?: (customSql: string) => void;
  isExecuting?: boolean;
}

const PALETTES = {
  emerald: ['#10B981', '#059669', '#34D399', '#047857', '#6EE7B7', '#065F46'],
  oceanic: ['#0284C7', '#0EA5E9', '#38BDF8', '#0369A1', '#7DD3FC', '#075985'],
  violet: ['#8B5CF6', '#A855F7', '#7C3AED', '#C084FC', '#6D28D9', '#DDD6FE'],
  amber: ['#F59E0B', '#D97706', '#FBBF24', '#B45309', '#FCD34D', '#92400E'],
};

export const QueryResponseCard: React.FC<QueryResponseCardProps> = ({
  question,
  sql,
  explanation,
  generatedBy = 'Deterministic Analytics Engine',
  rows = [],
  columns = [],
  rowCount,
  executionTimeSec,
  sqlExecutionTimeMs,
  visualization,
  onRunCustomSql,
  isExecuting = false,
}) => {
  // State
  const [copiedSql, setCopiedSql] = useState(false);
  const [copiedMd, setCopiedMd] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [isEditingSql, setIsEditingSql] = useState(false);
  const [editedSql, setEditedSql] = useState(sql);

  // Dynamic View Mode
  const initialView = (visualization?.chart_type === 'table' || !visualization?.chart_type)
    ? 'table'
    : (visualization.chart_type as 'bar' | 'line' | 'area' | 'pie' | 'table');
  const [activeView, setActiveView] = useState<'bar' | 'line' | 'area' | 'pie' | 'table'>(initialView);
  const [activePalette, setActivePalette] = useState<'emerald' | 'oceanic' | 'violet' | 'amber'>('emerald');
  const [selectedMetric, setSelectedMetric] = useState<string>('');

  // Table Filtering, Sorting & Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Reset editedSql if prop changes
  React.useEffect(() => {
    setEditedSql(sql);
  }, [sql]);

  // Keys & Numeric Key Identification
  const effectiveColumns = columns.length > 0 ? columns : (rows.length > 0 ? Object.keys(rows[0]) : []);

  const { numericKeys, textKeys, dateKeys } = useMemo(() => {
    if (!rows.length || !effectiveColumns.length) {
      return { numericKeys: [], textKeys: [], dateKeys: [] };
    }
    const sample = rows[0];
    const nKeys: string[] = [];
    const tKeys: string[] = [];
    const dKeys: string[] = [];

    effectiveColumns.forEach((col) => {
      const val = sample[col];
      const colLower = col.toLowerCase();
      if (['date', 'time', 'month', 'year', 'day'].some((k) => colLower.includes(k))) {
        dKeys.push(col);
      } else if (typeof val === 'number') {
        nKeys.push(col);
      } else if (typeof val === 'string' && val.trim() !== '' && !isNaN(Number(val))) {
        nKeys.push(col);
      } else {
        tKeys.push(col);
      }
    });

    return { numericKeys: nKeys, textKeys: tKeys, dateKeys: dKeys };
  }, [rows, effectiveColumns]);

  // Active X-Axis and Y-Axis
  const xAxisKey = useMemo(() => {
    if (visualization?.x_axis && effectiveColumns.includes(visualization.x_axis)) {
      return visualization.x_axis;
    }
    return dateKeys[0] || textKeys[0] || effectiveColumns[0] || '';
  }, [visualization, effectiveColumns, dateKeys, textKeys]);

  const activeYMetric = useMemo(() => {
    if (selectedMetric && numericKeys.includes(selectedMetric)) {
      return selectedMetric;
    }
    return numericKeys[0] || effectiveColumns[1] || effectiveColumns[0] || '';
  }, [selectedMetric, numericKeys, effectiveColumns]);

  // Sanitized Chart Data
  const chartData = useMemo(() => {
    return rows.map((r) => {
      const copy: Record<string, any> = { ...r };
      numericKeys.forEach((key) => {
        if (copy[key] !== null && copy[key] !== undefined) {
          const num = Number(copy[key]);
          if (!isNaN(num)) copy[key] = num;
        }
      });
      return copy;
    });
  }, [rows, numericKeys]);

  // Filtered and Sorted Table Data
  const filteredAndSortedRows = useMemo(() => {
    let list = [...rows];
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      list = list.filter((r) =>
        effectiveColumns.some((col) => String(r[col] ?? '').toLowerCase().includes(term))
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
  }, [rows, effectiveColumns, searchTerm, sortColumn, sortDirection]);

  const totalPages = Math.ceil(filteredAndSortedRows.length / rowsPerPage) || 1;
  const paginatedRows = filteredAndSortedRows.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  const handleSort = (col: string) => {
    if (sortColumn === col) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDirection('asc');
    }
  };

  // Copy Actions
  const handleCopySql = () => {
    navigator.clipboard.writeText(isEditingSql ? editedSql : sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleCopyMd = () => {
    if (!rows.length) return;
    const headerRow = `| ${effectiveColumns.join(' | ')} |`;
    const dividerRow = `| ${effectiveColumns.map(() => '---').join(' | ')} |`;
    const dataRows = rows
      .map((r) => `| ${effectiveColumns.map((c) => String(r[c] ?? '')).join(' | ')} |`)
      .join('\n');
    navigator.clipboard.writeText(`${headerRow}\n${dividerRow}\n${dataRows}`);
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 2000);
  };

  const handleCopyJson = () => {
    if (!rows.length) return;
    navigator.clipboard.writeText(JSON.stringify(rows, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const exportCSV = () => {
    if (!rows.length) return;
    const header = effectiveColumns.join(',');
    const csvLines = rows.map((r) =>
      effectiveColumns.map((c) => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(',')
    );
    const blob = new Blob([header + '\n' + csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_results_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleRunPlayground = () => {
    if (onRunCustomSql && editedSql.trim()) {
      onRunCustomSql(editedSql.trim());
      setIsEditingSql(false);
    }
  };

  const currentColors = PALETTES[activePalette];
  const isKpiCard = rows.length === 1 && effectiveColumns.length <= 2;

  return (
    <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981]/50 rounded-2xl p-4 sm:p-6 shadow-sm space-y-4 transition-all">
      {/* 1. MASTER CARD HEADER */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
        {/* Asked Question Title */}
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className="p-1.5 bg-[#ECFDF5] border border-[#10B981]/30 rounded-lg text-[#10B981] shrink-0">
            <HelpCircle className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-[10px] uppercase tracking-wider font-extrabold text-[#047857] block">
              QUERY QUESTION
            </span>
            <h2 className="text-sm sm:text-base font-bold text-[#0F172A] truncate">
              {question || 'Natural Language Query'}
            </h2>
          </div>
        </div>

        {/* Header Badges & Action Toolbar */}
        <div className="flex flex-wrap items-center gap-1.5 shrink-0">
          {/* Guard Passed Badge */}
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#047857] bg-[#ECFDF5] px-2.5 py-1 rounded-lg border border-[#10B981]/30 shadow-2xs">
            <ShieldCheck className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">Guard Passed</span>
          </span>

          {/* Execution Time Badge */}
          {(sqlExecutionTimeMs !== undefined || executionTimeSec !== undefined) && (
            <span className="flex items-center gap-1 text-[11px] text-[#64748B] bg-[#F8FAFC] px-2.5 py-1 rounded-lg border border-[#E2E8F0] font-mono">
              <Clock className="w-3 h-3 text-[#10B981]" />
              <span>{sqlExecutionTimeMs !== undefined ? `${sqlExecutionTimeMs}ms` : `${executionTimeSec}s`}</span>
            </span>
          )}

          {/* Rows Count */}
          <span className="text-[11px] text-[#64748B] bg-[#F8FAFC] px-2.5 py-1 rounded-lg border border-[#E2E8F0] font-mono">
            {rowCount !== undefined ? rowCount : rows.length} rows
          </span>

          <div className="h-4 w-px bg-[#E2E8F0] mx-0.5" />

          {/* Edit SQL Toggle */}
          <button
            onClick={() => {
              setIsEditingSql(!isEditingSql);
              if (!isEditingSql) setEditedSql(sql);
            }}
            className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg border transition-colors cursor-pointer font-medium ${
              isEditingSql
                ? 'bg-amber-50 text-amber-900 border-amber-300'
                : 'bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] border-[#E2E8F0]'
            }`}
            title="Edit and re-run SQL query"
          >
            <Edit3 className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">{isEditingSql ? 'Cancel' : 'Edit SQL'}</span>
          </button>

          {/* Copy SQL Button */}
          <button
            onClick={handleCopySql}
            className="flex items-center gap-1 text-xs bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-2.5 py-1 rounded-lg border border-[#E2E8F0] transition-colors cursor-pointer font-medium"
            title="Copy SQL to Clipboard"
          >
            {copiedSql ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
                <span className="text-[#047857] hidden sm:inline">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-[#64748B]" />
                <span className="hidden sm:inline">SQL</span>
              </>
            )}
          </button>

          {/* Copy Markdown Table */}
          {rows.length > 0 && (
            <button
              onClick={handleCopyMd}
              className="flex items-center gap-1 text-xs bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-2.5 py-1 rounded-lg border border-[#E2E8F0] transition-colors cursor-pointer font-medium"
              title="Copy Table as Markdown"
            >
              {copiedMd ? (
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
              ) : (
                <FileText className="w-3.5 h-3.5 text-[#0284C7]" />
              )}
              <span className="hidden sm:inline">MD</span>
            </button>
          )}

          {/* Copy JSON */}
          {rows.length > 0 && (
            <button
              onClick={handleCopyJson}
              className="flex items-center gap-1 text-xs bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-2.5 py-1 rounded-lg border border-[#E2E8F0] transition-colors cursor-pointer font-medium"
              title="Copy as JSON"
            >
              {copiedJson ? (
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
              ) : (
                <Code2 className="w-3.5 h-3.5 text-[#D97706]" />
              )}
              <span className="hidden sm:inline">JSON</span>
            </button>
          )}

          {/* Export CSV */}
          {rows.length > 0 && (
            <button
              onClick={exportCSV}
              className="flex items-center gap-1 text-xs bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-2.5 py-1 rounded-lg border border-[#E2E8F0] transition-colors cursor-pointer font-medium"
              title="Export to CSV"
            >
              <Download className="w-3.5 h-3.5 text-[#10B981]" />
              <span className="hidden sm:inline">CSV</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. AI EXECUTIVE BUSINESS INSIGHT & QUERY EXPLANATION */}
      {explanation && (
        <div className="p-3.5 bg-[#ECFDF5] border border-[#10B981]/30 rounded-xl space-y-1.5 text-xs text-[#0F172A] shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[#047857] font-bold text-xs">
              <Sparkles className="w-4 h-4 text-[#10B981]" />
              <span>AI BUSINESS INSIGHT & QUERY LOGIC</span>
            </div>
            {generatedBy && (
              <span className="text-[10px] text-[#047857] bg-[#FFFFFF] border border-[#10B981]/30 px-2.5 py-0.5 rounded-full font-semibold">
                Generated via <strong className="text-[#064E3B]">{generatedBy}</strong>
              </span>
            )}
          </div>
          <p className="text-[#047857] leading-relaxed font-medium pl-0.5">
            {explanation}
          </p>
        </div>
      )}

      {/* 3. SYNTHESIZED SQL QUERY STUDIO */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-[#047857]">
          <div className="flex items-center gap-2">
            <Code2 className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#047857]">
              SYNTHESIZED SQL QUERY
            </span>
            <span className="text-[10px] text-[#64748B] bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#E2E8F0] font-mono">
              ANSI SQLite
            </span>
          </div>
        </div>

        {/* Playground / Code Editor Mode */}
        {isEditingSql ? (
          <div className="space-y-2 bg-[#F8FAFC] p-3 rounded-xl border border-[#CBD5E1]">
            <textarea
              value={editedSql}
              onChange={(e) => setEditedSql(e.target.value)}
              rows={4}
              placeholder="Enter read-only SQL SELECT query..."
              className="w-full bg-[#FFFFFF] text-[#0F172A] font-mono text-xs p-3 rounded-lg border border-[#CBD5E1] focus:outline-none focus:border-[#10B981] resize-y"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E2E8F0] pt-2">
              <button
                onClick={() => setEditedSql(sql)}
                className="px-2.5 py-1 text-xs text-[#64748B] hover:text-[#0F172A] bg-[#FFFFFF] hover:bg-[#F1F5F9] border border-[#E2E8F0] rounded-lg cursor-pointer flex items-center gap-1 font-medium"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset to Generated</span>
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setIsEditingSql(false)}
                  className="px-3 py-1 text-xs text-[#64748B] bg-[#FFFFFF] hover:bg-[#F1F5F9] border border-[#E2E8F0] rounded-lg cursor-pointer font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRunPlayground}
                  disabled={isExecuting || !editedSql.trim()}
                  className="px-3.5 py-1 text-xs text-white font-bold bg-[#10B981] hover:bg-[#059669] rounded-lg flex items-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>{isExecuting ? 'Running...' : 'Run Custom SQL'}</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3 bg-[#F8FAFC] rounded-xl text-[#0F172A] font-mono text-xs border border-[#E2E8F0] leading-relaxed whitespace-pre-wrap break-words overflow-x-hidden shadow-2xs">
            <code>{sql || '-- No SQL query generated'}</code>
          </div>
        )}
      </div>

      {/* 4. VISUALIZATION OR DATA PRESENTATION */}
      {rows.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-[#E2E8F0]">
          {/* KPI Stat Cards if 1 row & <=2 cols */}
          {isKpiCard ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {effectiveColumns.map((k, idx) => (
                <div
                  key={k}
                  className="p-4 bg-[#FFFFFF] border border-[#E2E8F0] rounded-xl shadow-2xs flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <span className="text-[11px] uppercase font-bold text-[#047857] tracking-wider block">
                      {k.replace(/_/g, ' ')}
                    </span>
                    <span className="text-2xl sm:text-3xl font-black text-[#0F172A] font-mono">
                      {String(rows[0][k] ?? '0')}
                    </span>
                  </div>
                  <div className="p-2.5 bg-[#ECFDF5] border border-[#10B981]/30 rounded-xl text-[#10B981]">
                    {idx === 0 ? <TrendingUp className="w-5 h-5" /> : <Database className="w-5 h-5" />}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="w-full space-y-3">
              {/* Dynamic View & Palette Control Bar */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 bg-[#F8FAFC] p-2 rounded-xl border border-[#E2E8F0] text-xs">
                {/* View Mode Buttons */}
                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar pb-0.5 sm:pb-0 shrink-0">
                  <span className="text-[11px] text-[#047857] font-bold mr-1 shrink-0">View:</span>
                  {(['table', 'bar', 'line', 'area', 'pie'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setActiveView(type)}
                      className={`px-2.5 py-1 rounded-lg font-bold uppercase text-[10px] transition-colors shrink-0 cursor-pointer ${
                        activeView === type
                          ? 'bg-[#10B981] text-white shadow-2xs'
                          : 'text-[#047857] hover:text-[#0F172A] hover:bg-[#E2E8F0]'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>

                {/* Metric & Palette Selection Dropdowns */}
                <div className="flex flex-wrap items-center gap-2 justify-between sm:justify-end">
                  {numericKeys.length > 1 && activeView !== 'table' && (
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-[11px] text-[#047857] font-semibold shrink-0">Metric:</span>
                      <select
                        value={selectedMetric}
                        onChange={(e) => setSelectedMetric(e.target.value)}
                        className="bg-[#FFFFFF] text-xs text-[#0F172A] rounded border border-[#E2E8F0] px-2 py-1 focus:outline-none max-w-[130px] sm:max-w-[160px] truncate"
                      >
                        <option value="">{activeView === 'pie' ? 'Primary Metric' : 'All Metrics'}</option>
                        {numericKeys.map((k) => (
                          <option key={k} value={k}>
                            {k.replace(/_/g, ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {activeView !== 'table' && (
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-[11px] text-[#047857] font-semibold shrink-0">Palette:</span>
                      <select
                        value={activePalette}
                        onChange={(e) => setActivePalette(e.target.value as any)}
                        className="bg-[#FFFFFF] text-xs text-[#0F172A] rounded border border-[#E2E8F0] px-2 py-1 focus:outline-none"
                      >
                        <option value="emerald">Emerald</option>
                        <option value="oceanic">Oceanic Sky</option>
                        <option value="violet">Violet</option>
                        <option value="amber">Amber</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>

              {/* 1. Bar Chart View */}
              {activeView === 'bar' && (
                numericKeys.length > 0 ? (
                  <div className="h-64 sm:h-72 w-full pt-1 min-h-[260px]">
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey={xAxisKey} stroke="#475569" fontSize={11} />
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
                        {(selectedMetric ? [selectedMetric] : numericKeys).map((key, idx) => (
                          <Bar
                            key={key}
                            dataKey={key}
                            fill={currentColors[idx % currentColors.length]}
                            radius={[6, 6, 0, 0]}
                          />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 w-full flex flex-col items-center justify-center p-6 bg-[#F8FAFC] rounded-2xl border border-dashed border-[#CBD5E1] text-center space-y-2">
                    <Database className="w-8 h-8 text-[#94A3B8]" />
                    <p className="text-xs font-semibold text-[#0F172A]">No Numeric Metrics for Bar Chart</p>
                    <button
                      onClick={() => setActiveView('table')}
                      className="px-3 py-1 bg-[#10B981] text-white text-xs rounded-lg font-semibold cursor-pointer"
                    >
                      Switch to Table View
                    </button>
                  </div>
                )
              )}

              {/* 2. Line Chart View */}
              {activeView === 'line' && (
                numericKeys.length > 0 ? (
                  <div className="h-64 sm:h-72 w-full pt-1 min-h-[260px]">
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey={xAxisKey} stroke="#475569" fontSize={11} />
                        <YAxis stroke="#475569" fontSize={11} />
                        <Tooltip
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
                        {(selectedMetric ? [selectedMetric] : numericKeys).map((key, idx) => (
                          <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={currentColors[idx % currentColors.length]}
                            strokeWidth={3}
                            dot={{ r: 4 }}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 w-full flex flex-col items-center justify-center p-6 bg-[#F8FAFC] rounded-2xl border border-dashed border-[#CBD5E1] text-center space-y-2">
                    <TrendingUp className="w-8 h-8 text-[#94A3B8]" />
                    <p className="text-xs font-semibold text-[#0F172A]">No Numeric Metrics for Line Chart</p>
                    <button
                      onClick={() => setActiveView('table')}
                      className="px-3 py-1 bg-[#10B981] text-white text-xs rounded-lg font-semibold cursor-pointer"
                    >
                      Switch to Table View
                    </button>
                  </div>
                )
              )}

              {/* 3. Area Chart View */}
              {activeView === 'area' && (
                numericKeys.length > 0 ? (
                  <div className="h-64 sm:h-72 w-full pt-1 min-h-[260px]">
                    <ResponsiveContainer width="100%" height={260}>
                      <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey={xAxisKey} stroke="#475569" fontSize={11} />
                        <YAxis stroke="#475569" fontSize={11} />
                        <Tooltip
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
                        {(selectedMetric ? [selectedMetric] : numericKeys).map((key, idx) => (
                          <Area
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={currentColors[idx % currentColors.length]}
                            fill={currentColors[idx % currentColors.length]}
                            fillOpacity={0.25}
                          />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 w-full flex flex-col items-center justify-center p-6 bg-[#F8FAFC] rounded-2xl border border-dashed border-[#CBD5E1] text-center space-y-2">
                    <Database className="w-8 h-8 text-[#94A3B8]" />
                    <p className="text-xs font-semibold text-[#0F172A]">No Numeric Metrics for Area Chart</p>
                    <button
                      onClick={() => setActiveView('table')}
                      className="px-3 py-1 bg-[#10B981] text-white text-xs rounded-lg font-semibold cursor-pointer"
                    >
                      Switch to Table View
                    </button>
                  </div>
                )
              )}

              {/* 4. Pie Chart View */}
              {activeView === 'pie' && (
                numericKeys.length > 0 ? (
                  <div className="h-64 sm:h-72 w-full pt-1 min-h-[260px]">
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Tooltip
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
                        <Pie
                          data={chartData}
                          dataKey={activeYMetric}
                          nameKey={xAxisKey}
                          cx="50%"
                          cy="50%"
                          outerRadius={85}
                          label={({ name, percent }: any) =>
                            `${name ? String(name).slice(0, 12) : ''}: ${(((percent as number) || 0) * 100).toFixed(0)}%`
                          }
                        >
                          {chartData.map((_, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={currentColors[index % currentColors.length]}
                            />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 w-full flex flex-col items-center justify-center p-6 bg-[#F8FAFC] rounded-2xl border border-dashed border-[#CBD5E1] text-center space-y-2">
                    <PieIcon className="w-8 h-8 text-[#94A3B8]" />
                    <p className="text-xs font-semibold text-[#0F172A]">No Numeric Metrics for Pie Chart</p>
                    <button
                      onClick={() => setActiveView('table')}
                      className="px-3 py-1 bg-[#10B981] text-white text-xs rounded-lg font-semibold cursor-pointer"
                    >
                      Switch to Table View
                    </button>
                  </div>
                )
              )}

              {/* 5. Enterprise Data Table View */}
              {activeView === 'table' && (
                <div className="space-y-2.5 pt-1">
                  {/* Search & Pagination Control Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 bg-[#F8FAFC] p-2 rounded-xl border border-[#E2E8F0]">
                    <div className="relative flex-1 max-w-xs">
                      <Search className="w-3.5 h-3.5 text-[#10B981] absolute left-2.5 top-2" />
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => {
                          setSearchTerm(e.target.value);
                          setCurrentPage(1);
                        }}
                        placeholder="Search records..."
                        className="w-full bg-[#FFFFFF] border border-[#CBD5E1] rounded-lg pl-8 pr-2.5 py-1 text-xs text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#10B981]"
                      />
                    </div>

                    <div className="flex items-center gap-2 text-xs text-[#047857]">
                      <span className="text-[11px] font-mono font-semibold text-[#047857]">
                        Total: {filteredAndSortedRows.length} records
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

                  {/* Table Container */}
                  <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl bg-[#FFFFFF] shadow-2xs custom-scrollbar">
                    <table className="w-full text-xs text-left text-[#0F172A] border-collapse">
                      <thead className="bg-[#F8FAFC] text-[#047857] uppercase font-semibold border-b border-[#E2E8F0] sticky top-0">
                        <tr>
                          <th className="p-2.5 text-[10px] text-[#047857] w-8">#</th>
                          {effectiveColumns.map((col) => (
                            <th
                              key={col}
                              onClick={() => handleSort(col)}
                              className="p-2.5 cursor-pointer hover:text-[#0F172A] transition-colors select-none"
                            >
                              <div className="flex items-center gap-1 font-mono text-[11px]">
                                <span>{col}</span>
                                {sortColumn === col ? (
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
                            <td colSpan={effectiveColumns.length + 1} className="p-6 text-center text-slate-400 font-sans">
                              No matching records found.
                            </td>
                          </tr>
                        ) : (
                          paginatedRows.map((row, rowIdx) => (
                            <tr key={rowIdx} className="hover:bg-[#F1F5F9] transition-colors">
                              <td className="p-2.5 text-[10px] text-[#64748B]">
                                {(currentPage - 1) * rowsPerPage + rowIdx + 1}
                              </td>
                              {effectiveColumns.map((col) => (
                                <td key={col} className="p-2.5 text-[#0F172A] max-w-xs truncate">
                                  {String(row[col] ?? '')}
                                </td>
                              ))}
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination Footer */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between px-1 text-xs text-[#047857]">
                      <span className="text-[11px] font-mono font-medium text-[#047857]">
                        Page {currentPage} of {totalPages}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                          disabled={currentPage === 1}
                          className="p-1 bg-[#F8FAFC] hover:bg-[#E2E8F0] disabled:opacity-40 text-[#047857] rounded cursor-pointer border border-[#E2E8F0]"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                          disabled={currentPage === totalPages}
                          className="p-1 bg-[#F8FAFC] hover:bg-[#E2E8F0] disabled:opacity-40 text-[#047857] rounded cursor-pointer border border-[#E2E8F0]"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
