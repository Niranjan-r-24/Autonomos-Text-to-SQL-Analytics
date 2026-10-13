'use client';

import React from 'react';
import { Search, Sparkles, X, Terminal, Table as TableIcon, RefreshCw, Play, CornerDownLeft } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q?: string) => void;
  isExecuting: boolean;
  onOpenSchema?: () => void;
  tables?: string[];
}

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  setQuery,
  onSubmit,
  isExecuting,
  onOpenSchema,
  tables = ['sales', 'customers', 'products', 'audit_logs'],
}) => {
  const samplePrompts = [
    { label: 'Top 5 revenue products', category: 'Sales' },
    { label: 'Monthly sales trend by region', category: 'Trends' },
    { label: 'Customer distribution by plan & country', category: 'Customers' },
    { label: 'Recent failed audit log events', category: 'Security' },
    { label: 'Product category average ratings', category: 'Products' },
    { label: 'Sales revenue by region', category: 'Sales' },
  ];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isExecuting && query.trim()) {
      onSubmit();
    } else if (e.key === 'Escape') {
      setQuery('');
    }
  };

  return (
    <div className="w-full space-y-3.5">
      {/* Top Section Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#047857] uppercase tracking-wider mb-0.5">
            <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
            <span>Natural Language Query Interface</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-[#0F172A] tracking-tight">
            Ask Questions in Natural Language
          </h1>
        </div>

        {onOpenSchema && (
          <button
            onClick={onOpenSchema}
            className="flex items-center gap-1.5 text-xs text-[#047857] hover:text-[#0F172A] bg-[#ECFDF5] hover:bg-[#D1FAE5] px-3 py-1.5 rounded-xl border border-[#10B981]/30 font-semibold transition-colors cursor-pointer shadow-2xs"
          >
            <TableIcon className="w-3.5 h-3.5 text-[#10B981]" />
            <span>Explore Active Schema</span>
          </button>
        )}
      </div>

      {/* Terminal-Style Prompt Form Container */}
      <div className="relative bg-[#FFFFFF] border border-[#CBD5E1] focus-within:border-[#10B981] focus-within:ring-2 focus-within:ring-[#10B981]/20 rounded-2xl p-2 shadow-xs transition-all">
        <div className="flex items-center gap-2">
          {/* Terminal / SQL Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-[#047857] text-xs font-semibold shrink-0">
            <Terminal className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="font-mono text-[11px] font-bold">SQL</span>
          </div>

          {/* Text Input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question (e.g., 'Show top 5 revenue products' or 'Monthly sales by region')..."
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
                <span className="hidden sm:inline">Execute Query</span>
                <span className="sm:hidden">Run</span>
                <CornerDownLeft className="w-3 h-3 opacity-70 hidden md:inline" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quick Table Suggestion Chips & Sample Prompts */}
      <div className="space-y-2">
        {/* Table Chips */}
        {tables && tables.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto whitespace-nowrap no-scrollbar py-0.5 text-xs">
            <span className="font-bold text-[#047857] flex items-center gap-1 text-[10px] uppercase tracking-wider shrink-0 bg-[#ECFDF5] px-2 py-0.5 rounded-md border border-[#10B981]/20">
              <TableIcon className="w-3 h-3 text-[#10B981]" /> Tables:
            </span>
            {tables.map((tbl) => (
              <button
                key={tbl}
                type="button"
                onClick={() => {
                  const targetQ = `Show first 10 rows from ${tbl}`;
                  setQuery(targetQ);
                  onSubmit(targetQ);
                }}
                disabled={isExecuting}
                className="px-2.5 py-1 rounded-lg bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981] text-[#047857] hover:text-[#0F172A] font-mono text-[11px] cursor-pointer transition-all hover:bg-[#F8FAFC] shadow-2xs shrink-0 disabled:opacity-50"
                title={`Explore table '${tbl}'`}
              >
                +{tbl}
              </button>
            ))}
          </div>
        )}

        {/* Sample Prompt Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto whitespace-nowrap no-scrollbar py-0.5 text-xs">
          <span className="text-[10px] uppercase font-bold text-[#64748B] shrink-0 tracking-wider">
            Sample Queries:
          </span>
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(prompt.label);
                onSubmit(prompt.label);
              }}
              disabled={isExecuting}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#FFFFFF] hover:bg-[#F8FAFC] border border-[#E2E8F0] hover:border-[#10B981]/50 text-xs text-[#0F172A] font-medium transition-all shadow-2xs shrink-0 disabled:opacity-50 cursor-pointer"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
              <span>{prompt.label}</span>
              <span className="text-[9px] text-[#64748B] bg-[#F1F5F9] px-1.5 py-0.2 rounded font-mono">
                {prompt.category}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
