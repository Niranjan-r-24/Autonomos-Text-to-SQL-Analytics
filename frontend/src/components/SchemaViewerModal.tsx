'use client';

import React, { useState } from 'react';
import { Database, Table, Key, X, Layers, Hash, RefreshCw, CheckCircle2 } from 'lucide-react';

interface SchemaViewerModalProps {
  schema: Record<string, any>;
  isOpen: boolean;
  onClose: () => void;
  onReSeed?: () => void;
}

export const SchemaViewerModal: React.FC<SchemaViewerModalProps> = ({
  schema,
  isOpen,
  onClose,
  onReSeed
}) => {
  const [activeTable, setActiveTable] = useState<string>(
    Object.keys(schema)[0] || 'sales'
  );
  const [isSeeding, setIsSeeding] = useState(false);

  if (!isOpen) return null;

  const currentTableData = schema[activeTable] || { columns: [], sample_rows: [], row_count: 0 };

  const handleSeedTrigger = async () => {
    if (onReSeed) {
      setIsSeeding(true);
      await onReSeed();
      setIsSeeding(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-md p-4">
      <div className="w-full max-w-4xl bg-white rounded-3xl overflow-hidden shadow-2xl border border-slate-200 flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-slate-900 text-lime-400 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                Enterprise Schema Inspector
              </h2>
              <p className="text-xs text-slate-500">
                Pre-seeded PostgreSQL/SQLite Schema Metadata & Sample Data
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {onReSeed && (
              <button
                onClick={handleSeedTrigger}
                disabled={isSeeding}
                className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-slate-900 text-white text-xs font-bold shadow-sm transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin text-lime-400' : ''}`} />
                <span>{isSeeding ? 'Re-Seeding...' : 'Re-Seed Database'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-white text-slate-400 hover:text-slate-700 flex items-center justify-center border border-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Content Split Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Table List Sidebar */}
          <div className="w-56 border-r border-slate-200 bg-slate-50 p-4 space-y-2">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 px-2">
              Database Tables
            </span>
            {Object.keys(schema).map((table) => {
              const count = schema[table]?.row_count || 0;
              const isSelected = activeTable === table;
              return (
                <button
                  key={table}
                  onClick={() => setActiveTable(table)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs font-bold transition-all ${
                    isSelected
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-slate-200/60'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <Table className="w-4 h-4" />
                    <span>{table}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                      isSelected ? 'bg-lime-400 text-slate-900 font-extrabold' : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Table Details & Columns Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-white">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  Table: <span className="text-slate-900 font-mono underline">{activeTable}</span>
                </h3>
                <p className="text-xs text-slate-500">
                  Total Records: {currentTableData.row_count} • Columns: {currentTableData.columns?.length || 0}
                </p>
              </div>
            </div>

            {/* Column Schema Definitions */}
            <div>
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-slate-900" />
                Column Definitions
              </h4>
              <div className="grid grid-cols-2 gap-2.5 font-mono text-xs">
                {currentTableData.columns?.map((col: any) => (
                  <div
                    key={col.name}
                    className="p-3 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      {col.primary_key ? (
                        <Key className="w-3.5 h-3.5 text-lime-600 shrink-0" />
                      ) : (
                        <Hash className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                      <span className="text-slate-900 font-bold">{col.name}</span>
                    </div>
                    <span className="text-[11px] text-slate-600 bg-white px-2.5 py-0.5 rounded-full border border-slate-200">
                      {col.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Sample Data Rows */}
            {currentTableData.sample_rows && currentTableData.sample_rows.length > 0 && (
              <div>
                <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" />
                  Sample Records Context
                </h4>
                <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-100 text-slate-600 border-b border-slate-200">
                      <tr>
                        {currentTableData.columns?.map((c: any) => (
                          <th key={c.name} className="px-3 py-2">
                            {c.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-slate-800">
                      {currentTableData.sample_rows.map((row: any, rIdx: number) => (
                        <tr key={rIdx}>
                          {currentTableData.columns?.map((c: any) => (
                            <td key={c.name} className="px-3 py-2 whitespace-nowrap">
                              {String(row[c.name] ?? '')}
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
        </div>
      </div>
    </div>
  );
};
