'use client';

import React from 'react';
import { Search, Sparkles, X, RefreshCw, CornerDownLeft } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q?: string) => void;
  isExecuting: boolean;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  setQuery,
  onSubmit,
  isExecuting,
}) => {
  const samplePrompts = [
    { label: 'Top 5 revenue products', type: 'Highest' },
    { label: 'Which 3 products sold the highest quantity?', type: 'Quantity' },
    { label: 'Lowest 5 revenue products', type: 'Lowest' },
    { label: 'Monthly sales trend by region', type: 'Trend' },
  ];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isExecuting && query.trim()) {
      onSubmit();
    } else if (e.key === 'Escape') {
      setQuery('');
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* Prominent Search Input Box */}
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
            placeholder="Ask a question in plain English (e.g., 'Top 5 revenue products' or 'Lowest 5 revenue products')..."
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

      {/* 3-4 Sample Queries */}
      <div className="flex items-center gap-1.5 overflow-x-auto whitespace-nowrap no-scrollbar py-0.5 text-xs">
        <span className="text-[11px] font-semibold text-[#64748B] shrink-0 mr-1">
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
            <span className={`w-1.5 h-1.5 rounded-full ${prompt.type === 'Lowest' ? 'bg-amber-500' : 'bg-[#10B981]'}`} />
            <span>{prompt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
