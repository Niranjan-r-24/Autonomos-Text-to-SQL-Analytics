'use client';

import React, { useState } from 'react';
import { Database, Key, Table as TableIcon, ChevronRight, ChevronDown, RefreshCw, ArrowRight } from 'lucide-react';
import { SchemaInfo } from '@/types';

interface SchemaExplorerProps {
  schema: SchemaInfo | null;
  onRefresh: () => void;
  onSelectTableForQuery: (tableName: string) => void;
  isRefreshing: boolean;
}

export function SchemaExplorer({
  schema,
  onRefresh,
  onSelectTableForQuery,
  isRefreshing,
}: SchemaExplorerProps) {
  const [expandedTable, setExpandedTable] = useState<string | null>(null);

  if (!schema || !schema.table_names || schema.table_names.length === 0) {
    return (
      <div className="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-3">
        <Database className="w-8 h-8 text-slate-500 mx-auto" />
        <h3 className="text-sm font-medium text-slate-200">No database tables detected</h3>
        <p className="text-xs text-slate-400">
          Upload a CSV dataset or reseed the benchmark data to populate tables.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            Database Schema Explorer
          </h2>
          <p className="text-xs text-slate-400">
            Inspect real-time database tables, column types, foreign keys, and sample records.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Schema</span>
        </button>
      </div>

      {/* Relationships Badge */}
      {schema.relationships && schema.relationships.length > 0 && (
        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs space-y-1.5">
          <span className="font-semibold text-slate-300">Foreign Key Relationships:</span>
          <div className="flex flex-wrap gap-2 pt-1">
            {schema.relationships.map((rel, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700/80"
              >
                {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Table Cards List */}
      <div className="space-y-3">
        {schema.table_names.map((tblName) => {
          const tbl = schema.tables[tblName];
          const isExpanded = expandedTable === tblName;

          return (
            <div
              key={tblName}
              className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden transition-all"
            >
              {/* Table Header Bar */}
              <div
                onClick={() => setExpandedTable(isExpanded ? null : tblName)}
                className="px-5 py-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 select-none transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-slate-500">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </span>
                  <TableIcon className="w-4 h-4 text-emerald-400" />
                  <span className="font-mono text-sm font-semibold text-slate-200">{tblName}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                    {tbl?.row_count ?? 0} rows
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-mono">
                    {tbl?.columns?.length ?? 0} columns
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectTableForQuery(`Show all ${tblName}`);
                    }}
                    className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 px-2.5 py-1 rounded border border-emerald-500/20 transition-colors"
                  >
                    <span>Query</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Table Details Expansion */}
              {isExpanded && tbl && (
                <div className="p-5 border-t border-slate-800 bg-slate-950/50 space-y-4">
                  {/* Columns Table */}
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Columns & Schema
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                      {tbl.columns.map((col) => (
                        <div
                          key={col.name}
                          className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-xs font-mono"
                        >
                          <div className="flex items-center gap-1.5 overflow-hidden">
                            {col.primary_key && <Key className="w-3 h-3 text-amber-400 shrink-0" />}
                            <span className="text-slate-200 truncate">{col.name}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-sans uppercase shrink-0 px-1 rounded bg-slate-800">
                            {col.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Sample Rows Preview */}
                  {tbl.sample_rows && tbl.sample_rows.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Sample Records Preview
                      </h4>
                      <div className="overflow-x-auto border border-slate-800 rounded-lg">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-950 text-slate-400 font-mono text-[11px] border-b border-slate-800">
                            <tr>
                              {tbl.columns.map((col) => (
                                <th key={col.name} className="px-3 py-2 font-medium">
                                  {col.name}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                            {tbl.sample_rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-slate-900/60">
                                {tbl.columns.map((col) => (
                                  <td key={col.name} className="px-3 py-2 truncate max-w-[200px]">
                                    {String(row[col.name] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
