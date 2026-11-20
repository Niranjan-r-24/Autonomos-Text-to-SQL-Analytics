'use client';

import React, { useState, useEffect } from 'react';
import {
  Search,
  Play,
  Edit3,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Database,
  BarChart2,
  Table as TableIcon,
  Sparkles,
  ShieldCheck,
  RotateCcw,
  Layers,
  FileSpreadsheet,
  Copy,
  Check
} from 'lucide-react';
import { QueryResult, DatasetMetadata } from '@/types';
import { executeQuery, executeManualSql, formatErrorMessage } from '@/lib/api';
import { Visualizer } from '@/components/Visualizer';

interface QueryWorkspaceProps {
  onSuccessQuery: (result: QueryResult) => void;
  provider: string;
  apiKey: string;
  initialQuery?: string;
  datasets?: DatasetMetadata[];
  activeDataset?: DatasetMetadata | null;
  onSelectDataset?: (ds: DatasetMetadata | null) => void;
}

const BENCHMARK_QUESTIONS = [
  'How many customers are in the database?',
  'Show the first 10 products.',
  'Show all orders.',
  'Count orders by status.',
  'Which product generated the highest revenue?',
  'Show monthly revenue.',
  'Show audit logs.',
  'Show all nonexistent_records',
];

// Syntax highlighter for SQL queries
function renderHighlightedSql(sql: string) {
  const keywords = new Set([
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS',
    'GROUP', 'BY', 'ORDER', 'ASC', 'DESC', 'HAVING', 'LIMIT', 'OFFSET', 'AS', 'ON',
    'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL', 'LIKE', 'ILIKE', 'BETWEEN', 'EXISTS',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'UNION', 'ALL', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
    'DROP', 'ALTER', 'WITH', 'CAST', 'COALESCE', 'DATE', 'ROUND'
  ]);

  const regex = /('(?:''|[^'])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b|[^\s\w]+|\s+)/g;
  const parts = sql.match(regex) || [sql];

  return parts.map((part, index) => {
    const upper = part.toUpperCase();
    if (keywords.has(upper)) {
      return (
        <span key={index} className="text-forest-700 font-semibold">
          {part}
        </span>
      );
    }
    if (part.startsWith("'") && part.endsWith("'")) {
      return (
        <span key={index} className="text-amber-700">
          {part}
        </span>
      );
    }
    if (/^\d+(?:\.\d+)?$/.test(part)) {
      return (
        <span key={index} className="text-blue-700 font-mono">
          {part}
        </span>
      );
    }
    if (/^[=<>!+\-*/%,;()]+$/.test(part)) {
      return (
        <span key={index} className="text-stone-400">
          {part}
        </span>
      );
    }
    return (
      <span key={index} className="text-stone-800">
        {part}
      </span>
    );
  });
}

export function QueryWorkspace({
  onSuccessQuery,
  provider,
  apiKey,
  initialQuery = '',
  datasets = [],
  activeDataset = null,
  onSelectDataset,
}: QueryWorkspaceProps) {
  const [question, setQuestion] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'table' | 'chart'>('table');
  const [result, setResult] = useState<QueryResult | null>(null);

  // Selected dataset
  const [selectedDataset, setSelectedDataset] = useState<DatasetMetadata | null>(activeDataset || null);

  // SQL Editor state
  const [isEditingSql, setIsEditingSql] = useState(false);
  const [editableSql, setEditableSql] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  useEffect(() => {
    if (activeDataset) {
      setSelectedDataset(activeDataset);
    }
  }, [activeDataset]);

  useEffect(() => {
    if (initialQuery) {
      setQuestion(initialQuery);
      // If initialQuery mentions a table in datasets, bind it
      for (const ds of datasets) {
        if (initialQuery.toLowerCase().includes(ds.table_name.toLowerCase())) {
          setSelectedDataset(ds);
          break;
        }
      }
    }
  }, [initialQuery, datasets]);

  const handleRunQuery = async (queryText?: string) => {
    const q = queryText || question;
    if (!q.trim()) return;
    setResult(null);
    setLoading(true);
    setIsEditingSql(false);

    try {
      const targetTable = selectedDataset?.table_name;
      const targetId = selectedDataset?.dataset_id;

      const res = await executeQuery(q, provider, apiKey, targetTable, targetId);
      setResult(res);
      setEditableSql(res.sql || '');
      if (res.chart?.recommended) {
        setActiveTab('chart');
      } else {
        setActiveTab('table');
      }
      onSuccessQuery(res);
    } catch (err: any) {
      setResult({
        status: 'error',
        question: q,
        sql: '',
        error: formatErrorMessage(err, 'Network error occurred.'),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRunManualSql = async () => {
    if (!editableSql.trim()) return;
    setResult(null);
    setManualLoading(true);

    try {
      const res = await executeManualSql(editableSql);
      setResult(res);
      if (res.chart?.recommended) {
        setActiveTab('chart');
      } else {
        setActiveTab('table');
      }
      onSuccessQuery(res);
    } catch (err: any) {
      setResult({
        status: 'error',
        question: 'Manual SQL Execution',
        sql: editableSql,
        error: formatErrorMessage(err, 'Execution error.'),
      });
    } finally {
      setManualLoading(false);
    }
  };

  const handleDatasetChange = (ds: DatasetMetadata | null) => {
    setSelectedDataset(ds);
    setResult(null);
    if (onSelectDataset) {
      onSelectDataset(ds);
    }
    if (ds) {
      setQuestion(`Show all ${ds.table_name}`);
    }
  };

  const handleCopySql = () => {
    const textToCopy = isEditingSql ? editableSql : result?.sql;
    if (textToCopy && typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(textToCopy);
      setCopiedSql(true);
      setTimeout(() => setCopiedSql(false), 1500);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Workspace Card */}
      <div className="bg-white border border-stone-200/90 rounded-xl p-5 md:p-6 shadow-card space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-stone-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-forest-700" />
              <span>Natural Language SQL Query</span>
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Ask any question in plain English. Queries are grounded in the active database and persistent datasets.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {datasets.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-forest-800 bg-sage-50 border border-sage-200/80 px-2.5 py-1 rounded-md">
                <Layers className="w-3.5 h-3.5 text-forest-700" />
                <span>{datasets.length} dataset{datasets.length === 1 ? '' : 's'} registered</span>
              </div>
            )}
            <div className="flex items-center gap-1.5 text-xs text-forest-800 bg-sage-50 border border-sage-200/80 px-2.5 py-1 rounded-md">
              <ShieldCheck className="w-3.5 h-3.5 text-forest-700" />
              <span>Read-Only Guard Active</span>
            </div>
          </div>
        </div>

        {/* Dataset Selection Bar */}
        {datasets.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-stone-100">
            <span className="text-xs font-medium text-stone-500 flex items-center gap-1">
              <FileSpreadsheet className="w-3.5 h-3.5 text-forest-700" />
              <span>Target Dataset:</span>
            </span>
            <button
              type="button"
              onClick={() => handleDatasetChange(null)}
              className={`text-xs px-2.5 py-1 rounded-md transition-colors border ${
                selectedDataset === null
                  ? 'bg-sage-100 border-forest-600 text-forest-900 font-semibold shadow-xs'
                  : 'bg-stone-50 border-stone-200 text-stone-600 hover:text-stone-900 hover:bg-stone-100'
              }`}
            >
              All Tables
            </button>
            {datasets.map((ds) => {
              const isSelected = selectedDataset?.table_name === ds.table_name;
              return (
                <button
                  key={ds.dataset_id || ds.table_name}
                  type="button"
                  onClick={() => handleDatasetChange(ds)}
                  className={`text-xs px-2.5 py-1 rounded-md font-mono transition-colors border flex items-center gap-1.5 ${
                    isSelected
                      ? 'bg-sage-100 border-forest-600 text-forest-900 font-bold shadow-xs'
                      : 'bg-white border-stone-200 text-stone-700 hover:text-forest-800 hover:border-forest-600/50'
                  }`}
                >
                  <span>{ds.table_name}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-stone-100 text-stone-500 font-sans">
                    {ds.row_count} rows
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* Query Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRunQuery();
          }}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                selectedDataset
                  ? `e.g. Show all ${selectedDataset.table_name} or count ${selectedDataset.table_name}`
                  : 'e.g., Which product generated the highest revenue? or How many customers?'
              }
              className="w-full bg-stone-50/70 hover:bg-white focus:bg-white border border-stone-200/90 rounded-lg pl-10 pr-4 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600 transition-all shadow-subtle"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="flex items-center justify-center gap-2 bg-forest-900 hover:bg-forest-850 disabled:opacity-50 text-white font-medium text-sm px-5 py-2.5 rounded-lg transition-colors shadow-sm shrink-0"
          >
            <Play className={`w-3.5 h-3.5 text-emerald-300 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Analyzing...' : 'Generate & Run'}</span>
          </button>
        </form>

        {/* Suggested Benchmark Pills */}
        <div className="pt-1">
          <p className="text-xs font-medium text-stone-500 mb-2">Suggested Benchmark Questions:</p>
          <div className="flex flex-wrap gap-1.5">
            {BENCHMARK_QUESTIONS.map((bq) => (
              <button
                key={bq}
                type="button"
                onClick={() => {
                  setQuestion(bq);
                  handleRunQuery(bq);
                }}
                className="text-xs bg-stone-50 hover:bg-stone-100 text-stone-700 hover:text-stone-900 border border-stone-200/80 px-2.5 py-1 rounded-md transition-colors"
              >
                {bq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Query Loading State */}
      {(loading || manualLoading) && (
        <div className="bg-white border border-stone-200/90 rounded-xl p-8 shadow-card flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-forest-700 border-t-transparent animate-spin" />
          <p className="text-sm font-medium text-stone-700">Analyzing question and compiling visualization...</p>
          <p className="text-xs text-stone-400">Executing schema-grounded query against active dataset</p>
        </div>
      )}

      {/* Query Results & Execution Details */}
      {result && (
        <div className="space-y-4">
          {/* Status & Error Notification */}
          {result.status !== 'success' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-900 text-sm flex items-start gap-3 shadow-card">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900">
                  {result.status === 'blocked'
                    ? 'Security Policy Blocked Query'
                    : 'Query Generation or Execution Error'}
                </p>
                <p className="text-xs text-red-700 mt-1 font-mono">
                  {result.error
                    ? String(result.error)
                    : 'The backend encountered an issue executing this query. Please check that the server is online or try another question.'}
                </p>
              </div>
            </div>
          )}

          {/* Natural Language Answer Card */}
          {result.status === 'success' && result.answer && (
            <div className="p-5 bg-white border border-stone-200/90 rounded-xl space-y-2 shadow-card border-l-4 border-l-forest-700">
              <h3 className="text-xs font-semibold text-forest-800 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-forest-700" />
                <span>Executive Answer & Insights</span>
              </h3>
              <p className="text-sm text-stone-800 leading-relaxed font-normal">{result.answer}</p>
            </div>
          )}

          {/* Performance & Execution Telemetry */}
          {result.status === 'success' && (
            <div className="flex flex-wrap items-center gap-4 text-xs text-stone-500 px-1">
              <span className="flex items-center gap-1 font-mono">
                <Clock className="w-3.5 h-3.5 text-stone-400" />
                Pipeline Total: {result.execution_time_ms ?? 0} ms
              </span>
              {result.database_time_ms !== undefined && (
                <span className="flex items-center gap-1 font-mono">
                  <Database className="w-3.5 h-3.5 text-stone-400" />
                  Database Exec: {result.database_time_ms} ms
                </span>
              )}
              <span className="flex items-center gap-1 font-mono">
                <TableIcon className="w-3.5 h-3.5 text-stone-400" />
                Records Returned: {result.row_count ?? 0}
              </span>
            </div>
          )}

          {/* Results Tabs: Table View vs Visualizer Chart */}
          {result.status === 'success' && (
            <div className="bg-white border border-stone-200/90 rounded-xl overflow-hidden shadow-card">
              <div className="flex items-center justify-between border-b border-stone-200/80 px-4 bg-stone-50/60">
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveTab('table')}
                    className={`flex items-center gap-1.5 px-3.5 py-3 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === 'table'
                        ? 'border-forest-700 text-forest-800 font-semibold'
                        : 'border-transparent text-stone-500 hover:text-stone-800'
                    }`}
                  >
                    <TableIcon className="w-3.5 h-3.5" />
                    <span>Table Results ({result.row_count ?? 0})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('chart')}
                    className={`flex items-center gap-1.5 px-3.5 py-3 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === 'chart'
                        ? 'border-forest-700 text-forest-800 font-semibold'
                        : 'border-transparent text-stone-500 hover:text-stone-800'
                    }`}
                  >
                    <BarChart2 className="w-3.5 h-3.5" />
                    <span>Visualization</span>
                    {result.chart?.recommended && (
                      <span className="text-[10px] bg-sage-100 text-forest-800 px-1.5 py-0.2 rounded font-mono font-medium">
                        Auto
                      </span>
                    )}
                  </button>
                </div>
              </div>

              {/* Tab Views */}
              <div className="p-4 md:p-5">
                {activeTab === 'table' ? (
                  result.rows && result.rows.length > 0 ? (
                    <div className="overflow-x-auto border border-stone-200/80 rounded-lg">
                      <table className="w-full text-left text-xs text-stone-800">
                        <thead className="bg-stone-50 text-stone-600 font-mono text-[11px] border-b border-stone-200/80">
                          <tr>
                            {(result.columns || Object.keys(result.rows[0])).map((col) => (
                              <th key={col} className="px-3.5 py-2.5 font-medium tracking-tight">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-stone-100 font-mono text-[11px]">
                          {result.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-stone-50/80 transition-colors">
                              {(result.columns || Object.keys(row)).map((col) => (
                                <td key={col} className="px-3.5 py-2.5 whitespace-nowrap">
                                  {String(row[col] ?? '')}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-stone-400 text-xs font-mono">
                      Query returned 0 records.
                    </div>
                  )
                ) : (
                  <Visualizer
                    config={result.chart || null}
                    data={result.rows || []}
                    chartConfig={result.chart || null}
                    rows={result.rows || []}
                    columns={result.columns || []}
                  />
                )}
              </div>
            </div>
          )}

          {/* SQL Inspection / Editor Toolbar */}
          {result.sql && (
            <div className="bg-white border border-stone-200/90 rounded-xl overflow-hidden shadow-card">
              <div className="px-5 py-3 border-b border-stone-200/80 flex items-center justify-between bg-stone-50/60">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-stone-500" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-stone-700">
                    Executed SQL Query
                  </span>
                  {result.provider && (
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200">
                      Engine: {result.provider}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopySql}
                    className="flex items-center gap-1 text-xs text-stone-600 hover:text-stone-900 bg-white hover:bg-stone-50 border border-stone-200 px-2.5 py-1 rounded transition-colors shadow-subtle"
                    title="Copy SQL"
                  >
                    {copiedSql ? (
                      <>
                        <Check className="w-3 h-3 text-forest-700" />
                        <span className="text-forest-800">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 text-stone-500" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setIsEditingSql(!isEditingSql)}
                    className="flex items-center gap-1 text-xs text-stone-600 hover:text-stone-900 bg-white hover:bg-stone-50 border border-stone-200 px-2.5 py-1 rounded transition-colors shadow-subtle"
                  >
                    <Edit3 className="w-3 h-3 text-stone-500" />
                    <span>{isEditingSql ? 'Cancel Edit' : 'Edit SQL'}</span>
                  </button>
                </div>
              </div>

              {/* SQL Display or Edit Box */}
              <div className="p-4 bg-stone-50/60 font-mono text-xs">
                {isEditingSql ? (
                  <div className="space-y-3">
                    <textarea
                      value={editableSql}
                      onChange={(e) => setEditableSql(e.target.value)}
                      rows={4}
                      className="w-full bg-white border border-stone-300 rounded-lg p-3 text-stone-900 font-mono text-xs focus:outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600 leading-relaxed"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={handleRunManualSql}
                        disabled={manualLoading}
                        className="flex items-center gap-1.5 bg-forest-900 hover:bg-forest-850 text-white px-3.5 py-1.5 rounded-lg text-xs font-sans font-medium transition-colors shadow-sm"
                      >
                        <Play className={`w-3 h-3 text-emerald-300 ${manualLoading ? 'animate-spin' : ''}`} />
                        <span>{manualLoading ? 'Executing...' : 'Run Edited SQL'}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <pre className="overflow-x-auto whitespace-pre-wrap leading-relaxed py-1 px-1">
                    {renderHighlightedSql(result.sql)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
