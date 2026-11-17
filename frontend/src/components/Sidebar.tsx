'use client';

import React from 'react';
import {
  LayoutDashboard,
  Terminal,
  Database,
  UploadCloud,
  FileText,
  History,
  Settings,
  Sparkles,
} from 'lucide-react';

export type NavTab = 'overview' | 'query' | 'schema' | 'datasets' | 'rag' | 'history' | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  tableCount: number;
}

export function Sidebar({ activeTab, setActiveTab, tableCount }: SidebarProps) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'query', label: 'Query Workspace', icon: Terminal, badge: 'AI' },
    { id: 'schema', label: 'Schema Explorer', icon: Database, count: tableCount },
    { id: 'datasets', label: 'Dataset Upload', icon: UploadCloud },
    { id: 'rag', label: 'Document Intelligence', icon: FileText, badge: 'RAG' },
    { id: 'history', label: 'Query History', icon: History },
    { id: 'settings', label: 'Settings & Keys', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/90 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-lg border border-emerald-500/30">
            A
          </div>
          <div>
            <h1 className="font-semibold text-white tracking-wide text-sm flex items-center gap-1.5">
              Autonomos <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            </h1>
            <p className="text-xs text-slate-400">Text-to-SQL Analytics</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as NavTab)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {item.badge}
                  </span>
                )}
                {item.count !== undefined && item.count > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
        <p className="font-medium text-slate-400">Production Ready</p>
        <p className="mt-0.5">SQLite & PostgreSQL</p>
      </div>
    </aside>
  );
}
