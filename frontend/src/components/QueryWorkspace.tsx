'use client';

import React, { useState } from 'react';
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
} from 'lucide-react';
import { QueryResult } from '@/types';
import { executeQuery, executeManualSql } from '@/lib/api';
import { Visualizer } from '@/components/Visualizer';

interface QueryWorkspaceProps {
  onSuccessQuery: (result: QueryResult) => void;
  provider: string;
  apiKey: string;
  initialQuery?: string;
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
}: QueryWorkspaceProps) {
  const [question, setQuestion] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'table' | 'chart'>('table');
  const [result, setResult] = useState<QueryResult | null>(null);

  // SQL Editor state
  const [isEditingSql, setIsEditingSql] = useState(false);
  const [editableSql, setEditableSql] = useState('');
  const [manualLoading, setManualLoading] = useState(false);

  const handleRunQuery = async (queryText?: string) => {
    const q = queryText || question;
    if (!q.trim()) return;
    setLoading(true);
    setIsEditingSql(false);

    try {
      const res = await executeQuery(q, provider, apiKey);
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
        error: err?.response?.data?.detail || err.message || 'Network error occurred.',
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
        error: err?.response?.data?.detail || err.message || 'Execution error.',
      });
    } finally {
      setManualLoading(false);
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
              Ask any question in plain English. The schema-first engine identifies tables and returns grounded data.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Read-Only Guard Active</span>
          </div>
        </div>

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
              placeholder="e.g., Which product generated the highest revenue? or How many customers?"
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
                <p className="text-xs text-red-300/80 mt-1">{result.error}</p>
              </div>
            </div>
          )}

          {/* Natural Language Answer Card */}
          {result.status === 'success' && result.answer && (
            <div className="p-4 bg-slate-900 border border-emerald-500/30 rounded-xl flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/20">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Natural Language Insight
                </h4>
                <p className="text-sm font-medium text-slate-100 mt-1 leading-relaxed">
                  {result.answer}
                </p>
              </div>
            </div>
          )}

          {/* Generated SQL & Editor Panel */}
          {result.sql && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                  <Database className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Executed SQL Query</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsEditingSql(!isEditingSql)}
                    className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded transition-colors"
                  >
                    <Edit3 className="w-3 h-3" />
                    <span>{isEditingSql ? 'Cancel Edit' : 'Edit SQL'}</span>
                  </button>
                  {isEditingSql && (
                    <button
                      onClick={handleRunManualSql}
                      disabled={manualLoading}
                      className="flex items-center gap-1 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded transition-colors"
                    >
                      <Play className="w-3 h-3" />
                      <span>{manualLoading ? 'Running...' : 'Execute'}</span>
                    </button>
                  )}
                </div>
              </div>

              <div className="p-4 bg-slate-950 font-mono text-xs">
                {isEditingSql ? (
                  <textarea
                    value={editableSql}
                    onChange={(e) => setEditableSql(e.target.value)}
                    rows={4}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-3 text-emerald-300 focus:outline-none focus:border-emerald-500 font-mono text-xs leading-relaxed"
                  />
                ) : (
                  <pre className="text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                    {result.sql}
                  </pre>
                )}
              </div>

              {/* Execution Metrics Bar */}
              <div className="px-4 py-2 bg-slate-900/90 border-t border-slate-800 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  Total: {result.execution_time_ms} ms
                </span>
                {result.database_time_ms !== undefined && (
                  <span>DB Engine: {result.database_time_ms} ms</span>
                )}
                <span>Rows: {result.row_count}</span>
                {result.provider && (
                  <span className="capitalize px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                    Engine: {result.provider}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Results Tab View (Table vs Chart) */}
          {result.status === 'success' && result.rows && result.rows.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden space-y-4">
              <div className="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('table')}
                    className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded transition-colors ${
                      activeTab === 'table'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <TableIcon className="w-3.5 h-3.5" />
                    <span>Table View ({result.row_count})</span>
                  </button>
                  {result.chart?.recommended && (
                    <button
                      onClick={() => setActiveTab('chart')}
                      className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded transition-colors ${
                        activeTab === 'chart'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <BarChart2 className="w-3.5 h-3.5" />
                      <span>Chart Visualization</span>
                    </button>
                  )}
                </div>
              </div>

              {/* View Content */}
              <div className="p-4">
                {activeTab === 'chart' && result.chart ? (
                  <Visualizer config={result.chart} data={result.rows} />
                ) : (
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-slate-950 text-slate-400 font-medium uppercase border-b border-slate-800">
                        <tr>
                          {result.columns?.map((col) => (
                            <th key={col} className="px-4 py-3 font-semibold">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {result.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                            {result.columns?.map((col) => (
                              <td key={col} className="px-4 py-2.5 font-mono">
                                {typeof row[col] === 'number'
                                  ? Number(row[col]).toLocaleString()
                                  : String(row[col] ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
