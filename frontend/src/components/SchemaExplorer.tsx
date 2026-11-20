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
      <div className="p-8 md:p-12 bg-white border border-stone-200/90 rounded-xl text-center space-y-4 shadow-card max-w-2xl mx-auto">
        <div className="w-12 h-12 rounded-xl bg-sage-50 text-forest-700 flex items-center justify-center mx-auto border border-sage-200/80">
          <Database className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-stone-900">No database tables detected</h3>
        <p className="text-xs text-stone-500 max-w-md mx-auto leading-relaxed">
          Upload a CSV/document file in the Datasets workspace or reseed benchmark data to view tables.
        </p>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-forest-800 bg-sage-50 hover:bg-sage-100 px-3.5 py-2 rounded-lg border border-sage-200/90 transition-colors shadow-subtle"
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-stone-900 flex items-center gap-2">
            <Database className="w-4 h-4 text-forest-700" />
            <span>Database Schema Explorer</span>
          </h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Inspect live database tables, active uploaded files, column types, and sample records.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 text-xs font-medium text-stone-700 hover:text-stone-900 bg-white hover:bg-stone-50 px-3 py-1.5 rounded-lg border border-stone-200/90 transition-colors shadow-subtle shrink-0 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-stone-500 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Schema</span>
        </button>
      </div>

      {/* Uploaded Files & Custom Datasets Section */}
      {(uploadedFiles.length > 0 || customTables.length > 0) && (
        <div className="bg-white border border-sage-300/80 rounded-xl p-5 space-y-4 shadow-card">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-forest-900 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-forest-700" />
              <span>Uploaded Datasets & Document Tables ({uploadedFiles.length || customTables.length})</span>
            </h3>
            <span className="text-[11px] font-medium text-forest-800 bg-sage-50 px-2.5 py-0.5 rounded border border-sage-200/80">
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
                      className="p-3.5 bg-stone-50/70 border border-stone-200/80 hover:border-forest-600/40 rounded-lg transition-all space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 overflow-hidden">
                          {isDoc ? (
                            <FileText className="w-4 h-4 text-sky-600 shrink-0" />
                          ) : (
                            <FileSpreadsheet className="w-4 h-4 text-forest-700 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="font-mono text-xs font-semibold text-stone-900 truncate">
                              {item.table_name}
                            </p>
                            <p className="text-[11px] text-stone-500 truncate">
                              File: {item.filename}
                            </p>
                          </div>
                        </div>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded uppercase font-medium shrink-0 ${
                            isDoc
                              ? 'bg-sky-50 text-sky-700 border border-sky-200'
                              : 'bg-sage-50 text-forest-800 border border-sage-200'
                          }`}
                        >
                          {isDoc ? 'Document Table' : 'Dataset Table'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs text-stone-500 pt-1 border-t border-stone-200/60">
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
                            className="text-[11px] text-stone-500 hover:text-stone-800 underline cursor-pointer"
                          >
                            Inspect
                          </button>
                          <button
                            type="button"
                            onClick={() => onSelectTableForQuery(`Show all ${item.table_name}`)}
                            className="flex items-center gap-1 text-[11px] font-medium text-forest-800 hover:text-forest-900 bg-sage-50 hover:bg-sage-100 px-2 py-0.5 rounded border border-sage-200/70 transition-colors"
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
                      className="p-3.5 bg-stone-50/70 border border-stone-200/80 hover:border-forest-600/40 rounded-lg transition-all space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 overflow-hidden">
                          {isDoc ? (
                            <FileText className="w-4 h-4 text-sky-600 shrink-0" />
                          ) : (
                            <FileSpreadsheet className="w-4 h-4 text-forest-700 shrink-0" />
                          )}
                          <span className="font-mono text-xs font-semibold text-stone-900 truncate">
                            {tblName}
                          </span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded uppercase font-medium bg-sage-50 text-forest-800 border border-sage-200 shrink-0">
                          Uploaded Table
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs text-stone-500 pt-1 border-t border-stone-200/60">
                        <span className="font-mono text-[11px]">
                          {tbl?.row_count ?? 0} rows &bull; {tbl?.columns?.length ?? 0} cols
                        </span>
                        <button
                          type="button"
                          onClick={() => onSelectTableForQuery(`Show all ${tblName}`)}
                          className="flex items-center gap-1 text-[11px] font-medium text-forest-800 hover:text-forest-900 bg-sage-50 hover:bg-sage-100 px-2 py-0.5 rounded border border-sage-200/70 transition-colors"
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
        <div className="p-4 bg-white border border-stone-200/90 rounded-xl text-xs space-y-2 shadow-card">
          <span className="font-semibold text-stone-700 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-stone-500" />
            <span>Foreign Key Relationships:</span>
          </span>
          <div className="flex flex-wrap gap-2 pt-0.5">
            {schema.relationships.map((rel, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded bg-stone-50 text-stone-700 font-mono text-[11px] border border-stone-200"
              >
                {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* All Database Tables Header */}
      <div className="pt-1">
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-3">
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
              className={`bg-white border rounded-xl overflow-hidden transition-all shadow-card ${
                isUploaded
                  ? 'border-sage-300'
                  : 'border-stone-200/90'
              }`}
            >
              {/* Table Header Bar */}
              <div
                onClick={() => setExpandedTable(isExpanded ? null : tblName)}
                className="px-5 py-3.5 flex items-center justify-between cursor-pointer hover:bg-stone-50/70 select-none transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-stone-400">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </span>
                  {isDoc ? (
                    <FileText className="w-4 h-4 text-sky-600 shrink-0" />
                  ) : isUploaded ? (
                    <FileSpreadsheet className="w-4 h-4 text-forest-700 shrink-0" />
                  ) : (
                    <TableIcon className="w-4 h-4 text-stone-500 shrink-0" />
                  )}
                  <span className="font-mono text-sm font-semibold text-stone-900 truncate">{tblName}</span>

                  {isUploaded && (
                    <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded font-medium bg-sage-50 text-forest-800 border border-sage-200">
                      {isDoc ? 'Document Table' : 'Uploaded Dataset'}
                    </span>
                  )}

                  <span className="text-xs px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 font-mono">
                    {tbl?.row_count ?? 0} rows
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="hidden sm:inline text-xs text-stone-400 font-mono">
                    {tbl?.columns?.length ?? 0} columns
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectTableForQuery(`Show all ${tblName}`);
                    }}
                    className="flex items-center gap-1 text-xs font-medium text-forest-800 hover:text-forest-900 bg-sage-50 hover:bg-sage-100 px-2.5 py-1 rounded border border-sage-200 transition-colors"
                  >
                    <span>Query</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Table Details Expansion */}
              {isExpanded && tbl && (
                <div className="p-5 border-t border-stone-200/80 bg-stone-50/40 space-y-4">
                  {/* Columns Table */}
                  <div>
                    <h4 className="text-xs font-semibold text-stone-600 uppercase tracking-wider mb-2">
                      Columns & Schema
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                      {tbl.columns.map((col) => (
                        <div
                          key={col.name}
                          className="p-2.5 bg-white border border-stone-200 rounded-lg flex items-center justify-between text-xs font-mono shadow-subtle"
                        >
                          <div className="flex items-center gap-1.5 overflow-hidden">
                            {col.primary_key && <Key className="w-3 h-3 text-amber-600 shrink-0" />}
                            <span className="text-stone-800 font-medium truncate">{col.name}</span>
                          </div>
                          <span className="text-[10px] text-stone-500 font-sans uppercase shrink-0 px-1.5 py-0.2 rounded bg-stone-100">
                            {col.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Sample Rows Preview */}
                  {tbl.sample_rows && tbl.sample_rows.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-stone-600 uppercase tracking-wider mb-2">
                        Sample Records Preview
                      </h4>
                      <div className="overflow-x-auto border border-stone-200 rounded-lg bg-white shadow-subtle">
                        <table className="w-full text-left text-xs text-stone-800">
                          <thead className="bg-stone-50 text-stone-600 font-mono text-[11px] border-b border-stone-200">
                            <tr>
                              {tbl.columns.map((col) => (
                                <th key={col.name} className="px-3.5 py-2 font-medium tracking-tight">
                                  {col.name}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-stone-100 font-mono text-[11px]">
                            {tbl.sample_rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-stone-50/70 transition-colors">
                                {tbl.columns.map((col) => (
                                  <td key={col.name} className="px-3.5 py-2 truncate max-w-[200px]">
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
