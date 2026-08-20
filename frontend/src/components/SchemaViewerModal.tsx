'use client';

import React, { useState, useEffect } from 'react';
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
  onReSeed,
}) => {
  const tableNames = Object.keys(schema || {});
  const [activeTable, setActiveTable] = useState<string>('');
  const [isSeeding, setIsSeeding] = useState(false);

  useEffect(() => {
    if (tableNames.length > 0 && (!activeTable || !schema[activeTable])) {
      setActiveTable(tableNames[0]);
    }
  }, [schema, tableNames, activeTable]);

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl bg-white rounded-3xl overflow-hidden shadow-2xl border border-slate-200 flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-slate-900 text-lime-400 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                Database Schema Viewer
                <span className="px-2 py-0.5 rounded-full bg-lime-400 text-slate-900 text-[10px] font-bold uppercase">
                  {tableNames.length} Tables
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Inspect database tables, column data types, and sample records
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {onReSeed && (
              <button
                onClick={handleSeedTrigger}
                disabled={isSeeding}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin text-slate-900' : 'text-slate-600'}`} />
                <span>{isSeeding ? 'Re-Seeding...' : 'Reset Sample Data'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-white text-slate-400 hover:text-slate-700 flex items-center justify-center border border-slate-200 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Table List Sidebar */}
          <div className="w-60 border-r border-slate-200 bg-slate-50 p-4 space-y-1.5 overflow-y-auto">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 px-2 block mb-1">
              Tables
            </span>
            {tableNames.map((table) => {
              const count = schema[table]?.row_count || 0;
              const isSelected = activeTable === table;
              return (
                <button
                  key={table}
                  onClick={() => setActiveTable(table)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-2xl text-xs font-bold transition-all ${
                    isSelected
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-slate-200/60'
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <Table className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{table}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full shrink-0 ml-1 ${
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
          <div className="flex-1 p-6 overflow-y-auto space-y-5 bg-white">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  Table: <span className="font-mono text-slate-900 underline">{activeTable}</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Total Records: <strong className="text-slate-800">{currentTableData.row_count}</strong> • Columns: <strong className="text-slate-800">{currentTableData.columns?.length || 0}</strong>
                </p>
              </div>
            </div>

            {/* Column Schema Definitions */}
            <div>
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-slate-700" />
                Columns & Types
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-xs">
                {currentTableData.columns?.map((col: any) => (
                  <div
                    key={col.name}
                    className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      {col.primary_key ? (
                        <Key className="w-3.5 h-3.5 text-lime-600 shrink-0" title="Primary Key" />
                      ) : (
                        <Hash className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                      <span className="text-slate-900 font-bold">{col.name}</span>
                    </div>
                    <span className="text-[10px] text-slate-600 bg-white px-2 py-0.5 rounded-full border border-slate-200">
                      {col.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Sample Records */}
            {currentTableData.sample_rows && currentTableData.sample_rows.length > 0 && (
              <div>
                <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" />
                  Sample Data
                </h4>
                <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-100 text-slate-700 border-b border-slate-200 font-bold">
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
                        <tr key={rIdx} className="hover:bg-slate-100/60">
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
