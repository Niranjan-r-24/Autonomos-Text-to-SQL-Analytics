'use client';

import React from 'react';
import { Database, RefreshCw, Key, Sparkles, Menu } from 'lucide-react';

interface HeaderProps {
  onRefreshSchema: () => void;
  onReseedData: () => void;
  onOpenSettings: () => void;
  tableCount: number;
  provider: string;
  isRefreshing: boolean;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export function Header({
  onRefreshSchema,
  onReseedData,
  onOpenSettings,
  tableCount,
  provider,
  isRefreshing,
  onToggleSidebar,
  isSidebarOpen,
}: HeaderProps) {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-4">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors focus:outline-none"
            title={isSidebarOpen ? 'Collapse sidebar' : 'Show sidebar'}
            aria-label="Toggle sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div className="flex items-center gap-2 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Live Engine</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Database className="w-3.5 h-3.5" />
          <span>{tableCount} tables active</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Provider badge */}
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-md transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span className="capitalize">{provider || 'Schema Engine'}</span>
        </button>

        {/* Reseed benchmark data */}
        <button
          onClick={onReseedData}
          title="Reseed standard benchmark dataset (12 customers, 8 products, 30 orders)"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 px-2.5 py-1.5 rounded-md transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Reseed Benchmark</span>
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition-colors"
          title="Configure API Keys"
        >
          <Key className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
