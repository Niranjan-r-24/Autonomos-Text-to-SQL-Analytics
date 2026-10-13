'use client';

import React from 'react';
import { Database, Key, UploadCloud, RefreshCw, ShieldCheck, Terminal, Layers } from 'lucide-react';

interface HeaderProps {
  apiKey: string;
  provider: string;
  setProvider: (p: string) => void;
  onOpenSchema: () => void;
  onOpenApiKeyModal: () => void;
  onOpenUploadModal: () => void;
  onReSeed?: () => void;
  tableCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  apiKey,
  provider,
  setProvider,
  onOpenSchema,
  onOpenApiKeyModal,
  onOpenUploadModal,
  onReSeed,
  tableCount = 4,
}) => {
  return (
    <header className="w-full bg-[#FFFFFF] border-b border-[#E2E8F0] sticky top-0 z-40 shadow-xs">
      {/* Primary Header Row */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-[#0F172A] text-white flex items-center justify-center shadow-sm relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-tr from-[#10B981]/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="grid grid-cols-2 gap-1 w-4 h-4">
              <div className="bg-[#10B981] rounded-xs animate-pulse" />
              <div className="bg-white rounded-xs" />
              <div className="bg-white rounded-xs" />
              <div className="bg-[#10B981] rounded-xs" />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-baseline gap-1.5">
              <span className="text-base sm:text-lg font-black tracking-tight text-[#0F172A]">
                Text-to-SQL
              </span>
              <span className="text-base sm:text-lg font-black tracking-tight bg-gradient-to-r from-[#10B981] via-[#059669] to-[#047857] bg-clip-text text-transparent">
                Analytics
              </span>
            </div>
            <span className="px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-widest text-[#047857] bg-[#ECFDF5] border border-[#10B981]/30 rounded-md hidden xs:inline-block">
              AI 2.0
            </span>
          </div>
        </div>

        {/* Center / Status Indicators (Hidden on very small screens) */}
        <div className="hidden lg:flex items-center gap-2">
          {/* Active Database Pill */}
          <button
            onClick={onOpenSchema}
            className="flex items-center gap-1.5 text-xs bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-3 py-1.5 rounded-xl border border-[#E2E8F0] transition-colors cursor-pointer group shadow-2xs"
            title="Inspect Database Schema"
          >
            <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse shrink-0" />
            <span className="font-semibold text-slate-700 group-hover:text-slate-900">
              SQLite <span className="font-mono text-[#64748B] text-[11px]">(enterprise_analytics.db)</span>
            </span>
            <span className="text-[10px] bg-[#ECFDF5] text-[#047857] px-1.5 py-0.2 rounded-md font-bold border border-[#10B981]/30">
              {tableCount} tables
            </span>
          </button>

          {/* AST Guard Status Badge */}
          <div
            className="flex items-center gap-1.5 text-xs text-[#047857] bg-[#ECFDF5] px-3 py-1.5 rounded-xl border border-[#10B981]/30 font-medium shadow-2xs"
            title="Read-only SELECT enforcement & injection protection active"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="font-semibold">AST Guard Active</span>
          </div>
        </div>

        {/* Right Controls: Schema, Upload, Provider, API Key */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Schema Explorer Button */}
          <button
            onClick={onOpenSchema}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition-colors cursor-pointer shadow-2xs"
            title="Browse Database Tables & Columns"
          >
            <Database className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">Schema Explorer</span>
          </button>

          {/* Upload Dataset Button */}
          <button
            onClick={onOpenUploadModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#ECFDF5] text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] hover:border-[#10B981]/40 transition-colors cursor-pointer shadow-2xs"
            title="Import .CSV, .XLSX, .JSON, .DB, .SQL, .PARQUET datasets"
          >
            <UploadCloud className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">Upload Dataset</span>
            <span className="text-[9px] bg-[#ECFDF5] text-[#047857] px-1.5 py-0.2 rounded-md font-bold border border-[#10B981]/30 hidden md:inline">
              10+ formats
            </span>
          </button>

          {/* Provider Selector */}
          <div className="relative">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="bg-[#FFFFFF] border border-[#CBD5E1] text-[#0F172A] font-semibold px-2.5 sm:px-3 py-1.5 rounded-xl text-xs cursor-pointer focus:outline-none focus:border-[#10B981] focus:ring-1 focus:ring-[#10B981] shadow-2xs transition-colors"
            >
              <option value="gemini">Gemini 1.5 Flash</option>
              <option value="openai">OpenAI GPT-4o</option>
              <option value="fallback">Deterministic Offline</option>
            </select>
          </div>

          {/* API Key Modal Button */}
          <button
            onClick={onOpenApiKeyModal}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer shadow-2xs ${
              apiKey || provider === 'fallback'
                ? 'bg-[#ECFDF5] text-[#047857] border border-[#10B981]/40 hover:bg-[#D1FAE5]'
                : 'bg-[#0F172A] text-white hover:bg-slate-800'
            }`}
            title="Configure or test LLM API key"
          >
            <Key className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="hidden sm:inline">
              {apiKey ? 'API Key Active' : provider === 'fallback' ? 'Offline Engine' : 'Configure Key'}
            </span>
          </button>

          {/* Re-seed Button */}
          {onReSeed && (
            <button
              onClick={onReSeed}
              className="p-1.5 sm:px-2.5 sm:py-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A] border border-[#E2E8F0] text-xs font-medium transition-colors cursor-pointer"
              title="Reset sample enterprise database"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
