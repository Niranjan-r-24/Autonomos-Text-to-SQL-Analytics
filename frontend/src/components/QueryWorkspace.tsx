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
  FileSpreadsheet
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
    if (onSelectDataset) {
      onSelectDataset(ds);
    }
    if (ds) {
      setQuestion(`Show all ${ds.table_name}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              Natural Language SQL Query
            </h2>
            <p className="text-xs text-slate-400">
              Ask any question in plain English. Queries are grounded in the active database and persistent datasets.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {datasets.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded">
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
                <span>{datasets.length} dataset{datasets.length === 1 ? '' : 's'} registered</span>
              </div>
            )}
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Read-Only Guard Active</span>
            </div>
          </div>
        </div>

        {/* Dataset Selection Bar */}
        {datasets.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span>Target Dataset:</span>
            </span>
            <button
              type="button"
              onClick={() => handleDatasetChange(null)}
              className={`text-xs px-2.5 py-1 rounded-md transition-colors border ${
                selectedDataset === null
                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 font-semibold'
                  : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200'
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
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300 font-bold shadow-sm shadow-emerald-500/20'
                      : 'bg-slate-800/80 border-slate-700/60 text-slate-300 hover:text-emerald-400 hover:border-emerald-500/40'
                  }`}
                >
                  <span>{ds.table_name}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 font-sans">
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
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                selectedDataset
                  ? `e.g. Show all ${selectedDataset.table_name} or count ${selectedDataset.table_name}`
                  : 'e.g., Which product generated the highest revenue? or How many customers?'
              }
              className="w-full bg-slate-950 border border-slate-700/80 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm px-5 py-2.5 rounded-lg transition-colors"
          >
            <Play className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Analyzing...' : 'Generate & Run'}</span>
          </button>
        </form>

        {/* Suggested Benchmark Pills */}
        <div className="pt-2">
          <p className="text-xs font-medium text-slate-400 mb-2">Suggested Benchmark Questions:</p>
          <div className="flex flex-wrap gap-1.5">
            {BENCHMARK_QUESTIONS.map((bq) => (
              <button
                key={bq}
                type="button"
                onClick={() => {
                  setQuestion(bq);
                  handleRunQuery(bq);
                }}
                className="text-xs bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-emerald-400 border border-slate-700/60 hover:border-emerald-500/40 px-2.5 py-1 rounded-md transition-colors"
              >
                {bq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Query Results & Execution Details */}
      {result && (
        <div className="space-y-4">
          {/* Status & Error Notification */}
          {result.status !== 'success' && (
            <div className="p-4 bg-red-950/40 border border-red-500/40 rounded-xl text-red-200 text-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-300">
                  {result.status === 'blocked'
                    ? 'Security Policy Blocked Query'
                    : 'Query Generation or Execution Error'}
                </p>
                <p className="text-xs text-red-300/80 mt-1 font-mono">
                  {result.error
                    ? String(result.error)
                    : 'The backend encountered an issue executing this query. Please check that the server is online or try another question.'}
                </p>
              </div>
            </div>
          )}

          {/* Natural Language Answer Card */}
          {result.status === 'success' && result.answer && (
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
              <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Executive Answer & Insights
              </h3>
              <p className="text-sm text-slate-200 leading-relaxed font-normal">{result.answer}</p>
            </div>
          )}

          {/* Performance & Execution Telemetry */}
          {result.status === 'success' && (
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 px-1">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Pipeline Total: {result.execution_time_ms ?? 0} ms
              </span>
              {result.database_time_ms !== undefined && (
                <span className="flex items-center gap-1">
                  <Database className="w-3.5 h-3.5 text-slate-500" />
                  Database Exec: {result.database_time_ms} ms
                </span>
              )}
              <span className="flex items-center gap-1">
                <TableIcon className="w-3.5 h-3.5 text-slate-500" />
                Records Returned: {result.row_count ?? 0}
              </span>
            </div>
          )}

          {/* Results Tabs: Table View vs Visualizer Chart */}
          {result.status === 'success' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-800 px-4 bg-slate-950/40">
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveTab('table')}
                    className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === 'table'
                        ? 'border-emerald-500 text-emerald-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <TableIcon className="w-3.5 h-3.5" />
                    <span>Table Results ({result.row_count ?? 0})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('chart')}
                    className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === 'chart'
                        ? 'border-emerald-500 text-emerald-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <BarChart2 className="w-3.5 h-3.5" />
                    <span>Visualization</span>
                    {result.chart?.recommended && (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono">
                        Auto
                      </span>
                    )}
                  </button>
                </div>
              </div>

              {/* Tab Views */}
              <div className="p-4">
                {activeTab === 'table' ? (
                  result.rows && result.rows.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-950 text-slate-400 font-mono text-[11px] border-b border-slate-800">
                          <tr>
                            {(result.columns || Object.keys(result.rows[0])).map((col) => (
                              <th key={col} className="px-3.5 py-2.5 font-medium">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                          {result.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
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
                    <div className="text-center py-8 text-slate-500 text-xs font-mono">
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

          {/* SQL Inspection / Editor Toolbar (Placed at the bottom after answer and table) */}
          {result.sql && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold uppercase text-slate-300">
                    Executed SQL Query
                  </span>
                  {result.provider && (
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                      Engine: {result.provider}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsEditingSql(!isEditingSql)}
                    className="flex items-center gap-1 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded transition-colors"
                  >
                    <Edit3 className="w-3 h-3" />
                    <span>{isEditingSql ? 'Cancel Edit' : 'Edit SQL'}</span>
                  </button>
                </div>
              </div>

              {/* SQL Display or Edit Box */}
              <div className="p-4 bg-slate-950 font-mono text-xs">
                {isEditingSql ? (
                  <div className="space-y-3">
                    <textarea
                      value={editableSql}
                      onChange={(e) => setEditableSql(e.target.value)}
                      rows={4}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-slate-100 font-mono text-xs focus:outline-none focus:border-emerald-500"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={handleRunManualSql}
                        disabled={manualLoading}
                        className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-colors"
                      >
                        <Play className="w-3 h-3" />
                        <span>{manualLoading ? 'Executing...' : 'Run Edited SQL'}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <pre className="text-emerald-300 overflow-x-auto whitespace-pre-wrap">{result.sql}</pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
