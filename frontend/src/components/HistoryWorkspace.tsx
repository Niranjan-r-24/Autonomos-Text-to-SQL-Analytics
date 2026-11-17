'use client';

import React, { useEffect, useState } from 'react';
import { History, Trash2, RotateCcw, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { HistoryItem } from '@/types';
import { fetchQueryHistory, clearQueryHistory } from '@/lib/api';

interface HistoryWorkspaceProps {
  onRerunQuery: (question: string) => void;
}

export function HistoryWorkspace({ onRerunQuery }: HistoryWorkspaceProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const items = await fetchQueryHistory();
      setHistory(items);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    if (confirm('Clear all query execution history?')) {
      await clearQueryHistory();
      setHistory([]);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <History className="w-4 h-4 text-emerald-400" />
            Query Execution Audit & History
          </h2>
          <p className="text-xs text-slate-400">
            Log of natural-language and manual SQL queries, execution latency, and row counts.
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 rounded-lg border border-red-500/20 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Log</span>
          </button>
        )}
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading query history...</div>
      ) : history.length === 0 ? (
        <div className="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
          No query history recorded yet. Run a query in the Query Workspace to start tracking.
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-medium uppercase border-b border-slate-800 text-[11px]">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Question / Action</th>
                <th className="px-4 py-3">Generated SQL</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Latency</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              {history.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{item.timestamp}</td>
                  <td className="px-4 py-3 text-slate-200 font-sans font-medium max-w-[200px] truncate">
                    {item.question}
                  </td>
                  <td className="px-4 py-3 text-emerald-400 max-w-[240px] truncate">
                    {item.sql || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        item.status === 'success'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-red-500/10 text-red-400 border border-red-500/20'
                      }`}
                    >
                      {item.status === 'success' ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <AlertTriangle className="w-3 h-3" />
                      )}
                      <span>{item.status}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{item.duration_ms} ms</td>
                  <td className="px-4 py-3 text-slate-300">{item.row_count}</td>
                  <td className="px-4 py-3 text-right">
                    {item.question !== 'Manual SQL Execution' && (
                      <button
                        onClick={() => onRerunQuery(item.question)}
                        className="text-xs text-slate-400 hover:text-emerald-400 flex items-center gap-1 ml-auto font-sans"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Re-run</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
