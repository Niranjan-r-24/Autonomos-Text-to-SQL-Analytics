'use client';

import React from 'react';
import { Search, Sparkles, X, Plus, Calendar, Filter, ArrowUpRight } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q?: string) => void;
  isPipelineRunning: boolean;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  setQuery,
  onSubmit,
  isPipelineRunning,
}) => {
  const [selectedTag, setSelectedTag] = React.useState<string>('All');

  const promptTemplates = [
    { label: "Top 5 revenue products", tag: "Sales" },
    { label: "Monthly sales trend by region", tag: "Trends" },
    { label: "Customer distribution by plan & country", tag: "Customers" },
    { label: "Recent failed audit log events", tag: "Security" },
    { label: "Product category average ratings", tag: "Products" },
    { label: "Total sales count per customer", tag: "Sales" },
    { label: "Audit logs by severity level", tag: "Security" },
  ];

  const categories = ['All', 'Sales', 'Trends', 'Customers', 'Security', 'Products'];

  const filteredTemplates = selectedTag === 'All'
    ? promptTemplates
    : promptTemplates.filter((t) => t.tag === selectedTag);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isPipelineRunning) {
      onSubmit();
    }
  };

  return (
    <div className="w-full space-y-5">
      {/* Title Bar matching reference image ("Product Sales Performance") */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 mb-1">
            <span className="w-2 h-2 rounded-full bg-lime-400"></span>
            <span>Analytics Canvas</span>
            <span>/</span>
            <span>Text-to-SQL AI</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Product Sales Performance
          </h1>
        </div>

        {/* Toolbar Pills: Filters, Upload, Date Picker, Add Widget / Run Button */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category Filter Dropdown / Pill */}
          <div className="hidden md:flex items-center space-x-1.5 bg-white px-3 py-1.5 rounded-full border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat === 'All' ? 'All Filters' : cat}
                </option>
              ))}
            </select>
          </div>

          {/* Date Picker Pill */}
          <div className="flex items-center space-x-2 bg-white px-3.5 py-1.5 rounded-full border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>22.8.2026 - 28.8.2026</span>
          </div>

          {/* Add Widget / Run Query Button */}
          <button
            onClick={() => onSubmit()}
            disabled={isPipelineRunning || !query.trim()}
            className={`flex items-center space-x-2 px-5 py-2 rounded-full font-extrabold text-xs transition-all shadow-sm ${
              isPipelineRunning || !query.trim()
                ? 'bg-slate-900 text-white cursor-pointer hover:bg-slate-800'
                : 'bg-lime-400 text-slate-900 hover:bg-lime-300 shadow-lime-glow hover:scale-[1.02]'
            }`}
          >
            {isPipelineRunning ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin text-slate-900" />
                <span>Running Agents...</span>
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                <span>Execute Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Humanized Conversational AI Search Bar Canvas */}
      <div className="clay-card p-2 rounded-3xl flex items-center relative shadow-sm border border-slate-200">
        <div className="pl-4 text-slate-400">
          <Search className="w-5 h-5" />
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Orvion AI in plain English (e.g. 'Show top 5 revenue products with ratings')..."
          disabled={isPipelineRunning}
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
          disabled={isPipelineRunning || !query.trim()}
          className="mr-1 w-9 h-9 rounded-full bg-slate-900 hover:bg-slate-800 text-white flex items-center justify-center transition-all disabled:opacity-50 shrink-0"
        >
          <ArrowUpRight className="w-4 h-4 text-lime-400" />
        </button>
      </div>

      {/* Quick Prompt Template Chips & Category Filter Tabs */}
      <div className="flex flex-col space-y-2">
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-xs text-slate-400 font-bold whitespace-nowrap mr-1">
            Categories:
          </span>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedTag(cat)}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                selectedTag === cat
                  ? 'bg-slate-900 text-lime-400 shadow-sm'
                  : 'bg-white border border-slate-200 text-slate-600 hover:text-slate-900'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-xs text-slate-400 font-bold whitespace-nowrap mr-1">
            Templates:
          </span>
          {filteredTemplates.map((tpl, i) => (
            <button
              key={i}
              onClick={() => {
                setQuery(tpl.label);
                onSubmit(tpl.label);
              }}
              disabled={isPipelineRunning}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full clay-pill-inactive text-xs font-semibold whitespace-nowrap hover:border-slate-300"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-lime-400"></span>
              <span>{tpl.label}</span>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
                {tpl.tag}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
