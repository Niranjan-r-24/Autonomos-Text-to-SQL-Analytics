'use client';

import React from 'react';
import { Database, Key, UploadCloud, RefreshCw } from 'lucide-react';

interface HeaderProps {
  apiKey: string;
  provider: string;
  setProvider: (p: string) => void;
  onOpenSchema: () => void;
  onOpenApiKeyModal: () => void;
  onOpenUploadModal: () => void;
  onReSeed?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  apiKey,
  provider,
  setProvider,
  onOpenSchema,
  onOpenApiKeyModal,
  onOpenUploadModal,
  onReSeed,
}) => {
  return (
    <header className="w-full px-6 py-4 flex flex-wrap items-center justify-between gap-4 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-40">
      {/* Brand Logo & Connection Status */}
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-md">
          <div className="grid grid-cols-2 gap-0.5 w-4 h-4">
            <div className="bg-lime-400 rounded-xs"></div>
            <div className="bg-white rounded-xs"></div>
            <div className="bg-white rounded-xs"></div>
            <div className="bg-lime-400 rounded-xs"></div>
          </div>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-lg font-extrabold tracking-tight text-slate-900">
              Text-to-SQL Analytics
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-lime-400 text-slate-900">
              v2.0
            </span>
          </div>
          <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Database: <strong>SQLite (enterprise_analytics.db)</strong></span>
          </div>
        </div>
      </div>

      {/* Right Controls: Schema Viewer, Upload, Provider, API Key */}
      <div className="flex flex-wrap items-center gap-2.5">
        {/* View Database Schema Button */}
        <button
          onClick={onOpenSchema}
          className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold shadow-sm transition-all hover:border-slate-300"
        >
          <Database className="w-3.5 h-3.5 text-lime-600" />
          <span>View Database Schema</span>
        </button>

        {/* Upload Dataset Button */}
        <button
          onClick={onOpenUploadModal}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all"
        >
          <UploadCloud className="w-3.5 h-3.5 text-slate-600" />
          <span>Upload Dataset</span>
        </button>

        {/* Provider Selector */}
        <div className="relative">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="bg-white border border-slate-200 text-slate-800 font-semibold px-3 py-1.5 rounded-full text-xs cursor-pointer focus:outline-none shadow-sm hover:border-slate-300"
          >
            <option value="gemini">Gemini 1.5 Flash</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="fallback">Deterministic Engine</option>
          </select>
        </div>

        {/* API Key Modal Button */}
        <button
          onClick={onOpenApiKeyModal}
          className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all shadow-sm ${
            apiKey || provider === 'fallback'
              ? 'bg-lime-400 text-slate-900 border border-lime-500/40 hover:bg-lime-300'
              : 'bg-slate-900 text-white hover:bg-slate-800'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>{apiKey ? 'API Key Configured' : provider === 'fallback' ? 'Offline Engine' : 'Set API Key'}</span>
        </button>
      </div>
    </header>
  );
};
