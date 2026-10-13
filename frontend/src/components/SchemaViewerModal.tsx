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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl bg-[#FFFFFF] rounded-2xl overflow-hidden shadow-2xl border border-[#E2E8F0] flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center shadow-2xs">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[#0F172A] flex items-center gap-2">
                Schema Explorer
                <span className="px-2 py-0.5 rounded-md bg-[#ECFDF5] text-[#047857] text-[10px] font-bold border border-[#10B981]/30 uppercase">
                  {tableNames.length} Tables Connected
                </span>
              </h2>
              <p className="text-xs text-[#64748B]">
                Inspect relational tables, column definitions, and sample records
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {onReSeed && (
              <button
                onClick={handleSeedTrigger}
                disabled={isSeeding}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#FFFFFF] hover:bg-[#F1F5F9] text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin text-[#10B981]' : 'text-[#64748B]'}`} />
                <span>{isSeeding ? 'Re-Seeding...' : 'Reset Sample Data'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg text-[#64748B] hover:text-[#0F172A] hover:bg-[#E2E8F0] flex items-center justify-center transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Table List Sidebar */}
          <div className="w-60 border-r border-[#E2E8F0] bg-[#F8FAFC] p-3 space-y-1.5 overflow-y-auto custom-scrollbar">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#047857] px-2 block mb-1">
              Database Tables
            </span>
            {tableNames.map((table) => {
              const count = schema[table]?.row_count || 0;
              const isSelected = activeTable === table;
              return (
                <button
                  key={table}
                  onClick={() => setActiveTable(table)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#ECFDF5] border border-[#10B981]/40 text-[#047857] shadow-2xs'
                      : 'text-[#475569] hover:bg-[#F1F5F9] hover:text-[#0F172A] border border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <Table className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-[#10B981]' : 'text-[#94A3B8]'}`} />
                    <span className="truncate">{table}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded-md shrink-0 ml-1 ${
                      isSelected
                        ? 'bg-[#10B981] text-white font-bold'
                        : 'bg-[#E2E8F0] text-[#64748B]'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Table Details & Columns Area */}
          <div className="flex-1 p-5 sm:p-6 overflow-y-auto space-y-5 bg-[#FFFFFF] custom-scrollbar">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
              <div>
                <h3 className="text-sm font-bold text-[#0F172A] flex items-center gap-2">
                  Table: <span className="font-mono text-[#047857] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#10B981]/30">{activeTable}</span>
                </h3>
                <p className="text-xs text-[#64748B] mt-1 font-mono">
                  Rows: <strong className="text-[#0F172A]">{currentTableData.row_count}</strong> • Columns: <strong className="text-[#0F172A]">{currentTableData.columns?.length || 0}</strong>
                </p>
              </div>
            </div>

            {/* Column Schema Definitions */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#047857] mb-2.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-[#10B981]" />
                Columns & Data Types
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-xs">
                {currentTableData.columns?.map((col: any) => (
                  <div
                    key={col.name}
                    className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      {col.primary_key ? (
                        <Key className="w-3.5 h-3.5 text-[#10B981] shrink-0" title="Primary Key" />
                      ) : (
                        <Hash className="w-3.5 h-3.5 text-[#94A3B8] shrink-0" />
                      )}
                      <span className="text-[#0F172A] font-semibold">{col.name}</span>
                    </div>
                    <span className="text-[10px] text-[#047857] bg-[#FFFFFF] px-2 py-0.5 rounded-md border border-[#E2E8F0]">
                      {col.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Sample Records */}
            {currentTableData.sample_rows && currentTableData.sample_rows.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#047857] mb-2.5 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                  Sample Records
                </h4>
                <div className="overflow-x-auto rounded-xl border border-[#E2E8F0] bg-[#FFFFFF] custom-scrollbar">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[#F8FAFC] text-[#047857] border-b border-[#E2E8F0] font-semibold">
                      <tr>
                        {currentTableData.columns?.map((c: any) => (
                          <th key={c.name} className="px-3 py-2">
                            {c.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0] text-[#0F172A]">
                      {currentTableData.sample_rows.map((row: any, rIdx: number) => (
                        <tr key={rIdx} className="hover:bg-[#F1F5F9] transition-colors">
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
