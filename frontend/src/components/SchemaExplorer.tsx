'use client';

import React, { useState } from 'react';
import {
  Database,
  Key,
  Table as TableIcon,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  ArrowRight,
  FileSpreadsheet,
  FileText,
  Sparkles,
  Layers
} from 'lucide-react';
import { SchemaInfo, UploadedFileInfo } from '@/types';

interface SchemaExplorerProps {
  schema: SchemaInfo | null;
  onRefresh: () => void;
  onSelectTableForQuery: (tableName: string) => void;
  isRefreshing: boolean;
}

const SEED_TABLES = new Set(['customers', 'orders', 'order_items', 'products', 'audit_logs']);

export function SchemaExplorer({
  schema,
  onRefresh,
  onSelectTableForQuery,
  isRefreshing,
}: SchemaExplorerProps) {
  const [expandedTable, setExpandedTable] = useState<string | null>(null);

  if (!schema || !schema.table_names || schema.table_names.length === 0) {
    return (
      <div className="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-4">
        <Database className="w-10 h-10 text-slate-500 mx-auto" />
        <h3 className="text-sm font-medium text-slate-200">No database tables detected</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Upload a CSV/document file in the Datasets workspace or reseed benchmark data to view tables.
        </p>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 px-3 py-1.5 rounded-lg border border-emerald-500/20 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Check Again</span>
        </button>
      </div>
    );
  }

  // Identify all custom or uploaded tables
  const uploadedFiles: UploadedFileInfo[] = schema.uploaded_files || [];
  const uploadedTableNames = new Set(uploadedFiles.map((u) => u.table_name.toLowerCase()));

  // Any non-seed table is also considered an uploaded table
  const customTables = schema.table_names.filter(
    (t) => !SEED_TABLES.has(t.toLowerCase()) || uploadedTableNames.has(t.toLowerCase())
  );

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
            Inspect live database tables, active uploaded files, column types, and sample records.
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

      {/* Uploaded Files & Custom Datasets Section */}
      {(uploadedFiles.length > 0 || customTables.length > 0) && (
        <div className="bg-slate-900/90 border border-emerald-500/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Uploaded Datasets & Document Tables ({uploadedFiles.length || customTables.length})</span>
            </h3>
            <span className="text-[11px] text-emerald-400/80 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              Active in Database
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {uploadedFiles.length > 0
              ? uploadedFiles.map((item, idx) => {
                  const tbl = schema.tables?.[item.table_name];
                  const isDoc = item.file_type === 'document' || item.table_name.startsWith('doc_');
                  return (
                    <div
                      key={idx}
                      className="p-3.5 bg-slate-950/80 border border-slate-800 hover:border-emerald-500/40 rounded-lg transition-all space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 overflow-hidden">
                          {isDoc ? (
                            <FileText className="w-4 h-4 text-sky-400 shrink-0" />
                          ) : (
                            <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="font-mono text-xs font-semibold text-slate-200 truncate">
                              {item.table_name}
                            </p>
                            <p className="text-[11px] text-slate-400 truncate">
                              File: {item.filename}
                            </p>
                          </div>
                        </div>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded uppercase font-medium shrink-0 ${
                            isDoc
                              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}
                        >
                          {isDoc ? 'Document Table' : 'Dataset Table'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                        <span className="font-mono text-[11px]">
                          {tbl?.row_count ?? item.row_count} rows &bull;{' '}
                          {tbl?.columns?.length ?? item.column_count ?? 0} cols
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setExpandedTable(item.table_name);
                              const elem = document.getElementById(`table-card-${item.table_name}`);
                              if (elem) elem.scrollIntoView({ behavior: 'smooth' });
                            }}
                            className="text-[11px] text-slate-400 hover:text-slate-200 underline cursor-pointer"
                          >
                            Inspect
                          </button>
                          <button
                            type="button"
                            onClick={() => onSelectTableForQuery(`Show all ${item.table_name}`)}
                            className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 px-2 py-0.5 rounded transition-colors"
                          >
                            <span>Query</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              : customTables.map((tblName) => {
                  const tbl = schema.tables?.[tblName];
                  const isDoc = tblName.startsWith('doc_');
                  return (
                    <div
                      key={tblName}
                      className="p-3.5 bg-slate-950/80 border border-slate-800 hover:border-emerald-500/40 rounded-lg transition-all space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 overflow-hidden">
                          {isDoc ? (
                            <FileText className="w-4 h-4 text-sky-400 shrink-0" />
                          ) : (
                            <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
                          )}
                          <span className="font-mono text-xs font-semibold text-slate-200 truncate">
                            {tblName}
                          </span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded uppercase font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                          Uploaded Table
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                        <span className="font-mono text-[11px]">
                          {tbl?.row_count ?? 0} rows &bull; {tbl?.columns?.length ?? 0} cols
                        </span>
                        <button
                          type="button"
                          onClick={() => onSelectTableForQuery(`Show all ${tblName}`)}
                          className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded transition-colors"
                        >
                          <span>Query</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
          </div>
        </div>
      )}

      {/* Foreign Key Relationships */}
      {schema.relationships && schema.relationships.length > 0 && (
        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs space-y-1.5">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Foreign Key Relationships:</span>
          </span>
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

      {/* All Database Tables Header */}
      <div className="pt-2">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          All Active Database Tables ({schema.table_names.length})
        </h3>
      </div>

      {/* Table Cards List */}
      <div className="space-y-3">
        {schema.table_names.map((tblName) => {
          const tbl = schema.tables?.[tblName];
          const isExpanded = expandedTable === tblName;
          const isUploaded =
            !SEED_TABLES.has(tblName.toLowerCase()) || uploadedTableNames.has(tblName.toLowerCase());
          const isDoc = tblName.startsWith('doc_');

          return (
            <div
              key={tblName}
              id={`table-card-${tblName}`}
              className={`bg-slate-900 border rounded-xl overflow-hidden transition-all ${
                isUploaded
                  ? 'border-emerald-500/30 shadow-sm shadow-emerald-950/20'
                  : 'border-slate-800'
              }`}
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
                  {isDoc ? (
                    <FileText className="w-4 h-4 text-sky-400" />
                  ) : isUploaded ? (
                    <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <TableIcon className="w-4 h-4 text-slate-400" />
                  )}
                  <span className="font-mono text-sm font-semibold text-slate-200">{tblName}</span>

                  {isUploaded && (
                    <span className="text-[10px] px-2 py-0.5 rounded font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {isDoc ? 'Document Table' : 'Uploaded Dataset'}
                    </span>
                  )}

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
