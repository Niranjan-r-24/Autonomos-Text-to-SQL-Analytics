'use client';

import React, { useMemo } from 'react';
import { Search, Sparkles, X, RefreshCw, CornerDownLeft, Database, Layers } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q?: string) => void;
  isExecuting: boolean;
  activeTable?: string | null;
  tables?: string[];
  tableColumns?: string[];
  onSelectTable?: (tbl: string | null) => void;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  setQuery,
  onSubmit,
  isExecuting,
  activeTable,
  tables = [],
  tableColumns = [],
  onSelectTable,
}) => {
  // Compute dynamic sample queries tailored to the active table's actual columns
  const samplePrompts = useMemo(() => {
    if (!activeTable) {
      return [
        { label: 'Top 5 revenue products', type: 'Highest' },
        { label: 'Which 3 products sold the highest quantity?', type: 'Quantity' },
        { label: 'Lowest 5 revenue products', type: 'Lowest' },
        { label: 'Monthly sales trend by region', type: 'Trend' },
      ];
    }

    const cols = tableColumns || [];
    const numCols = cols.filter((c) =>
      ['price', 'salary', 'score', 'amount', 'total', 'revenue', 'units', 'rating', 'quantity', 'age', 'cost', 'mileage'].some((k) =>
        c.toLowerCase().includes(k)
      )
    );
    const textCols = cols.filter(
      (c) => !numCols.includes(c) && !c.toLowerCase().endsWith('_id') && c.toLowerCase() !== 'id'
    );

    const prompts = [
      { label: `Show first 10 rows from ${activeTable}`, type: 'Browse' }
    ];

    if (numCols.length > 0) {
      const metric = numCols[0];
      prompts.push({ label: `Top 5 highest ${metric.replace(/_/g, ' ')}`, type: 'Highest' });
      prompts.push({ label: `What is the average ${metric.replace(/_/g, ' ')}?`, type: 'Average' });
      if (textCols.length > 0) {
        prompts.push({ label: `Average ${metric.replace(/_/g, ' ')} by ${textCols[0].replace(/_/g, ' ')}`, type: 'Group' });
      }
    } else if (textCols.length > 0) {
      prompts.push({ label: `Count records by ${textCols[0].replace(/_/g, ' ')}`, type: 'Count' });
    }

    return prompts.slice(0, 4);
  }, [activeTable, tableColumns]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isExecuting && query.trim()) {
      onSubmit();
    } else if (e.key === 'Escape') {
      setQuery('');
    }
  };

  return (
    <div className="w-full space-y-2.5">
      {/* 1. Active Dataset & Table Selector Bar */}
      {tables.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] flex items-center gap-1 shrink-0 mr-1">
              <Database className="w-3 h-3 text-[#10B981]" />
              Active Table:
            </span>

            {/* Auto-detect button */}
            <button
              onClick={() => onSelectTable?.(null)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                !activeTable
                  ? 'bg-[#10B981] text-white shadow-2xs font-bold'
                  : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
              }`}
            >
              Auto-Detect
            </button>

            {/* Individual table buttons */}
            {tables
              .filter((tbl) => !['audit_logs', 'sqlite_sequence'].includes(tbl.toLowerCase()))
              .map((tbl) => {
              const isSelected = activeTable === tbl;
              const isCustom = !['sales', 'products', 'customers', 'employees', 'orders', 'order_items', 'payments', 'support_tickets'].includes(tbl.toLowerCase());
              return (
                <button
                  key={tbl}
                  onClick={() => onSelectTable?.(tbl)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer shrink-0 ${
                    isSelected
                      ? 'bg-[#ECFDF5] text-[#047857] border border-[#10B981]/50 font-bold shadow-2xs ring-1 ring-[#10B981]/30'
                      : 'bg-[#FFFFFF] border border-[#E2E8F0] text-[#334155] hover:bg-[#F8FAFC]'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-[#10B981] animate-pulse' : 'bg-[#94A3B8]'}`} />
                  <span>{tbl}</span>
                  {isCustom && (
                    <span className="text-[9px] px-1 py-0.2 bg-[#10B981]/20 text-[#047857] rounded uppercase font-mono font-bold">
                      CSV
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {activeTable && (
            <span className="text-[10px] font-mono text-[#047857] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#10B981]/20 hidden md:inline">
              Focusing on: <strong className="font-bold">{activeTable}</strong>
            </span>
          )}
        </div>
      )}

      {/* 2. Prominent Search Input Box */}
      <div className="relative bg-[#FFFFFF] border border-[#CBD5E1] focus-within:border-[#10B981] focus-within:ring-2 focus-within:ring-[#10B981]/20 rounded-2xl p-2 shadow-xs transition-all">
        <div className="flex items-center gap-2">
          {/* Search Icon */}
          <div className="pl-2 text-[#94A3B8] shrink-0">
            <Search className="w-4 h-4 text-[#10B981]" />
          </div>

          {/* Text Input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeTable
                ? `Ask questions about ${activeTable} (e.g. 'Show first 10 rows', 'What is the average...', 'Top 5...')...`
                : "Ask any analytical question in plain English (e.g. 'Top 5 revenue products' or upload your own CSV)..."
            }
            disabled={isExecuting}
            className="w-full bg-transparent border-none px-2 py-1.5 text-xs sm:text-sm text-[#0F172A] placeholder:text-[#94A3B8] font-medium focus:outline-none min-w-0"
          />

          {/* Clear input button */}
          {query && !isExecuting && (
            <button
              onClick={() => setQuery('')}
              className="text-[#94A3B8] hover:text-[#0F172A] p-1.5 rounded-lg transition-colors cursor-pointer shrink-0"
              title="Clear input"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {/* Execute Query Button */}
          <button
            onClick={() => onSubmit()}
            disabled={isExecuting || !query.trim()}
            className="bg-[#10B981] hover:bg-[#059669] disabled:bg-[#F1F5F9] disabled:text-[#94A3B8] text-white font-bold px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-xl flex items-center gap-2 text-xs transition-all cursor-pointer shrink-0 shadow-md shadow-[#10B981]/20 border border-[#10B981]/30 active:scale-95 disabled:shadow-none disabled:border-transparent"
          >
            {isExecuting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span className="hidden sm:inline">Executing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Run Query</span>
                <span className="sm:hidden">Run</span>
                <CornerDownLeft className="w-3 h-3 opacity-70 hidden md:inline" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3. Dynamic Sample Queries */}
      <div className="flex items-center gap-1.5 overflow-x-auto whitespace-nowrap no-scrollbar py-0.5 text-xs">
        <span className="text-[11px] font-semibold text-[#64748B] shrink-0 mr-1 flex items-center gap-1">
          <Layers className="w-3 h-3 text-[#10B981]" />
          Sample queries:
        </span>
        {samplePrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => {
              setQuery(prompt.label);
              onSubmit(prompt.label);
            }}
            disabled={isExecuting}
            className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[#FFFFFF] hover:bg-[#F8FAFC] border border-[#E2E8F0] hover:border-[#10B981]/50 text-xs text-[#1E293B] font-medium transition-all shadow-2xs shrink-0 disabled:opacity-50 cursor-pointer"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                prompt.type === 'Lowest'
                  ? 'bg-amber-500'
                  : prompt.type === 'Browse'
                  ? 'bg-sky-500'
                  : 'bg-[#10B981]'
              }`}
            />
            <span>{prompt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
