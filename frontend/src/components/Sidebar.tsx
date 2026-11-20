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
  Menu,
} from 'lucide-react';

export type NavTab = 'overview' | 'query' | 'schema' | 'datasets' | 'rag' | 'history' | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  tableCount: number;
  isOpen?: boolean;
  onToggle?: () => void;
}

export function Sidebar({
  activeTab,
  setActiveTab,
  tableCount,
  isOpen = true,
  onToggle,
}: SidebarProps) {
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
    <aside
      className={`h-screen bg-forest-900 border-forest-800/80 flex flex-col justify-between shrink-0 select-none transition-all duration-300 ease-in-out overflow-hidden z-20 shadow-lg ${
        isOpen
          ? 'w-64 border-r opacity-100'
          : 'w-0 border-r-0 opacity-0 pointer-events-none'
      }`}
    >
      <div
        className={`w-64 min-w-[16rem] h-full flex flex-col justify-between transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Brand Header */}
          <div className="h-16 flex items-center justify-between px-5 border-b border-forest-800/90 shrink-0 bg-forest-950/40">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-300 flex items-center justify-center font-bold text-sm border border-emerald-500/30 shrink-0 shadow-inner">
                A
              </div>
              <div className="min-w-0">
                <h1 className="font-semibold text-white tracking-tight text-sm flex items-center gap-1.5 truncate">
                  <span>Autonomos</span>
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                </h1>
                <p className="text-[11px] text-emerald-100/60 font-normal truncate">Text-to-SQL Analytics</p>
              </div>
            </div>
            {onToggle && (
              <button
                type="button"
                onClick={onToggle}
                className="p-1.5 text-emerald-200/70 hover:text-white hover:bg-forest-800 rounded-lg transition-colors focus:outline-none"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <Menu className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Navigation Items */}
          <div className="flex-1 overflow-y-auto sidebar-scroll p-3 space-y-1">
            <div className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-200/40">
              Platform Navigation
            </div>
            <nav className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id as NavTab)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                      isActive
                        ? 'bg-forest-800 text-white shadow-sm border border-emerald-600/30'
                        : 'text-emerald-100/70 hover:text-white hover:bg-forest-850'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Icon
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? 'text-emerald-300' : 'text-emerald-200/60 group-hover:text-emerald-200'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {item.badge && (
                        <span
                          className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                            isActive
                              ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/30'
                              : 'bg-forest-950/60 text-emerald-300/80 border border-forest-800'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                      {item.count !== undefined && item.count > 0 && (
                        <span
                          className={`text-[11px] font-mono px-2 py-0.2 rounded-full ${
                            isActive
                              ? 'bg-forest-950/80 text-emerald-200'
                              : 'bg-forest-950/50 text-emerald-200/70'
                          }`}
                        >
                          {item.count}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Footer Info */}
          <div className="p-4 border-t border-forest-800/80 bg-forest-950/30 shrink-0">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-medium text-emerald-100/80">Engine Status</span>
              <span className="inline-flex items-center gap-1.5 text-[10px] text-emerald-300 bg-forest-800/60 px-2 py-0.5 rounded border border-forest-700/50">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Production
              </span>
            </div>
            <p className="mt-1 text-[10px] text-emerald-100/50 font-mono">SQLite &bull; PostgreSQL</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
