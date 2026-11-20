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
    <header className="h-16 border-b border-stone-200/80 bg-white/95 backdrop-blur px-6 md:px-8 flex items-center justify-between shrink-0 z-10">
      <div className="flex items-center gap-3 md:gap-4">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className="p-1.5 text-stone-500 hover:text-stone-800 hover:bg-stone-100 rounded-lg transition-colors focus:outline-none"
            title={isSidebarOpen ? 'Collapse sidebar' : 'Show sidebar'}
            aria-label="Toggle sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        {/* Engine status pill */}
        <div className="flex items-center gap-2 text-xs font-medium text-forest-800 bg-sage-50 border border-sage-200/90 px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-forest-600 animate-pulse" />
          <span className="font-medium tracking-tight">Live Engine</span>
        </div>

        {/* Table count */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-stone-500">
          <Database className="w-3.5 h-3.5 text-stone-400" />
          <span>{tableCount} tables active</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {/* Provider badge button */}
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 text-xs font-medium text-stone-700 bg-stone-50 hover:bg-stone-100 border border-stone-200/90 px-3 py-1.5 rounded-md transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-forest-600" />
          <span className="capitalize">{provider || 'Schema Engine'}</span>
        </button>

        {/* Reseed benchmark data */}
        <button
          onClick={onReseedData}
          title="Reseed standard benchmark dataset (12 customers, 8 products, 30 orders)"
          className="flex items-center gap-1.5 text-xs font-medium text-stone-600 hover:text-stone-900 bg-white hover:bg-stone-50 border border-stone-200/90 px-3 py-1.5 rounded-md transition-colors shadow-subtle"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-stone-500 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Reseed Benchmark</span>
          <span className="sm:hidden">Reseed</span>
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="p-1.5 text-stone-500 hover:text-stone-800 hover:bg-stone-100 border border-transparent hover:border-stone-200 rounded-md transition-colors"
          title="Configure API Keys"
        >
          <Key className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
