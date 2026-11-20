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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-stone-900 flex items-center gap-2">
            <History className="w-4 h-4 text-forest-700" />
            <span>Query Execution Audit & History</span>
          </h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Log of natural-language and manual SQL queries, execution latency, and row counts.
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1.5 text-xs font-medium text-red-700 hover:text-red-800 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg border border-red-200 transition-colors shadow-subtle shrink-0 self-start sm:self-auto"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Log</span>
          </button>
        )}
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-stone-400 font-mono">Loading query history...</div>
      ) : history.length === 0 ? (
        <div className="p-8 md:p-12 bg-white border border-stone-200/90 rounded-xl text-center text-xs text-stone-500 shadow-card max-w-xl mx-auto">
          No query history recorded yet. Run a query in the Query Workspace to start tracking.
        </div>
      ) : (
        <div className="bg-white border border-stone-200/90 rounded-xl overflow-hidden shadow-card">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-stone-800">
              <thead className="bg-stone-50 text-stone-600 font-mono text-[11px] uppercase tracking-wider border-b border-stone-200">
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
              <tbody className="divide-y divide-stone-100 font-mono text-[11px]">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-stone-50/70 transition-colors">
                    <td className="px-4 py-3 text-stone-500 whitespace-nowrap">{item.timestamp}</td>
                    <td className="px-4 py-3 text-stone-900 font-sans font-medium max-w-[200px] truncate">
                      {item.question}
                    </td>
                    <td className="px-4 py-3 text-forest-700 max-w-[240px] truncate">
                      {item.sql || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          item.status === 'success'
                            ? 'bg-sage-50 text-forest-800 border border-sage-200'
                            : 'bg-red-50 text-red-700 border border-red-200'
                        }`}
                      >
                        {item.status === 'success' ? (
                          <CheckCircle2 className="w-3 h-3 text-forest-700" />
                        ) : (
                          <AlertTriangle className="w-3 h-3 text-red-600" />
                        )}
                        <span>{item.status}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-stone-500">{item.duration_ms} ms</td>
                    <td className="px-4 py-3 text-stone-800 font-semibold">{item.row_count}</td>
                    <td className="px-4 py-3 text-right">
                      {item.question !== 'Manual SQL Execution' && (
                        <button
                          onClick={() => onRerunQuery(item.question)}
                          className="text-xs text-stone-500 hover:text-forest-800 flex items-center gap-1 ml-auto font-sans font-medium transition-colors"
                        >
                          <RotateCcw className="w-3 h-3 text-stone-400" />
                          <span>Re-run</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
