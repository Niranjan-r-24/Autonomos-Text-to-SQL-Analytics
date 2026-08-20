'use client';

import React from 'react';
import { Search, Sparkles, X, ArrowUpRight, Database, Play } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q?: string) => void;
  isExecuting: boolean;
  onOpenSchema?: () => void;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  setQuery,
  onSubmit,
  isExecuting,
  onOpenSchema,
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
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Header with Title & Schema Viewer Trigger */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 mb-1">
            <span className="w-2 h-2 rounded-full bg-lime-500 animate-pulse"></span>
            <span>Natural Language Interface</span>
            <span>/</span>
            <span>Text-to-SQL Analytics</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Ask Questions in Plain English
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          {onOpenSchema && (
            <button
              onClick={onOpenSchema}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold shadow-sm transition-all hover:border-slate-300"
            >
              <Database className="w-3.5 h-3.5 text-lime-600" />
              <span>View Database Schema</span>
            </button>
          )}

          <button
            onClick={() => onSubmit()}
            disabled={isExecuting || !query.trim()}
            className={`flex items-center space-x-2 px-5 py-2 rounded-full font-extrabold text-xs transition-all shadow-sm ${
              isExecuting || !query.trim()
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-lime-400 text-slate-900 hover:bg-lime-300 hover:scale-[1.02] shadow-sm'
            }`}
          >
            {isExecuting ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin text-slate-900" />
                <span>Generating & Executing...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Query</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Search Input Box */}
      <div className="clay-card p-2 rounded-3xl flex items-center bg-white relative shadow-sm border border-slate-200 focus-within:ring-2 focus-within:ring-lime-400/50">
        <div className="pl-4 text-slate-400">
          <Search className="w-5 h-5" />
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. 'Show top 5 revenue products' or 'Monthly sales by region'..."
          disabled={isExecuting}
          className="w-full bg-transparent px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 font-medium focus:outline-none"
        />

        {query && (
          <button
            onClick={() => setQuery('')}
            className="text-slate-400 hover:text-slate-600 px-2"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={() => onSubmit()}
          disabled={isExecuting || !query.trim()}
          className="mr-1 w-9 h-9 rounded-full bg-slate-900 hover:bg-slate-800 text-white flex items-center justify-center transition-all disabled:opacity-40 shrink-0"
        >
          <ArrowUpRight className="w-4 h-4 text-lime-400" />
        </button>
      </div>

      {/* Quick Sample Question Chips */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-xs text-slate-400 font-bold whitespace-nowrap mr-1">
          Sample Questions:
        </span>
        {samplePrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => {
              setQuery(prompt.label);
              onSubmit(prompt.label);
            }}
            disabled={isExecuting}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 whitespace-nowrap transition-all hover:border-slate-300 disabled:opacity-50"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-lime-400"></span>
            <span>{prompt.label}</span>
            <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
              {prompt.category}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
