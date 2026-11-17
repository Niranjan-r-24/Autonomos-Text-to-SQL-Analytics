'use client';

import React, { useMemo } from 'react';
import {
  Database,
  Terminal,
  UploadCloud,
  FileText,
  ShieldCheck,
  TrendingUp,
  Package,
  ArrowRight,
} from 'lucide-react';
import { SchemaInfo } from '@/types';
import { NavTab } from '@/components/Sidebar';

interface OverviewProps {
  schema: SchemaInfo | null;
  onNavigate: (tab: NavTab) => void;
  onRunQuickQuery: (q: string) => void;
}

export function Overview({ schema, onNavigate, onRunQuickQuery }: OverviewProps) {
  const tableCount = Array.isArray(schema?.table_names) ? schema.table_names.length : 0;
  
  const totalRows = useMemo(() => {
    if (!schema?.tables || typeof schema.tables !== 'object') return 0;
    try {
      return Object.values(schema.tables).reduce((acc, t) => {
        const count = t && typeof t === 'object' && typeof t.row_count === 'number' ? t.row_count : 0;
        return acc + count;
      }, 0);
    } catch {
      return 0;
    }
  }, [schema]);

  const quickStats = [
    {
      title: 'Active Tables',
      value: tableCount,
      icon: Database,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
    {
      title: 'Total Ingested Records',
      value: totalRows > 0 ? totalRows.toLocaleString('en-US') : '0',
      icon: TrendingUp,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
    },
    {
      title: 'SQL Safety Guard',
      value: 'Read-Only Strict',
      icon: ShieldCheck,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
      border: 'border-indigo-500/20',
    },
    {
      title: 'Database Engine',
      value: 'SQLite / PostgreSQL',
      icon: Package,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    },
  ];

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Welcome Banner */}
      <div className="p-6 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/20 rounded-2xl">
        <h2 className="text-xl font-bold text-white tracking-tight">
          Enterprise AI Text-to-SQL Analytics
        </h2>
        <p className="text-sm text-slate-300 mt-1 max-w-2xl leading-relaxed">
          Ask questions in plain English, introspect live schemas, upload multi-format CSV datasets,
          and execute validated analytical queries with zero hallucinated tables.
        </p>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            onClick={() => onNavigate('query')}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
          >
            <Terminal className="w-4 h-4" />
            <span>Launch Query Workspace</span>
          </button>
          <button
            onClick={() => onNavigate('datasets')}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-4 py-2 rounded-lg border border-slate-700 transition-colors"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New CSV</span>
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {quickStats.map((st) => {
          const Icon = st.icon;
          return (
            <div
              key={st.title}
              className={`p-4 bg-slate-900 border ${st.border} rounded-xl space-y-1.5`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">{st.title}</span>
                <div className={`p-1.5 rounded-lg ${st.bg} ${st.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <p className="text-lg font-bold text-slate-100 font-mono">{st.value}</p>
            </div>
          );
        })}
      </div>

      {/* Feature Navigation Cards */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Analytics Capabilities</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            onClick={() => onNavigate('query')}
            className="p-5 bg-slate-900 border border-slate-800 hover:border-emerald-500/40 rounded-xl cursor-pointer transition-all group space-y-2"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Terminal className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-slate-100 group-hover:text-emerald-400 transition-colors flex items-center justify-between">
              <span>Text-to-SQL Engine</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Schema-grounded translation of natural language queries with automatic chart generation.
            </p>
          </div>

          <div
            onClick={() => onNavigate('schema')}
            className="p-5 bg-slate-900 border border-slate-800 hover:border-blue-500/40 rounded-xl cursor-pointer transition-all group space-y-2"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-slate-100 group-hover:text-blue-400 transition-colors flex items-center justify-between">
              <span>Schema Introspection</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 transition-colors" />
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Browse table schemas, inferred column data types, foreign keys, and preview records.
            </p>
          </div>

          <div
            onClick={() => onNavigate('rag')}
            className="p-5 bg-slate-900 border border-slate-800 hover:border-purple-500/40 rounded-xl cursor-pointer transition-all group space-y-2"
          >
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-slate-100 group-hover:text-purple-400 transition-colors flex items-center justify-between">
              <span>Document Intelligence</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 transition-colors" />
            </h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload enterprise policies or reports for grounded RAG QA with strict citations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
