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
  Sparkles,
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
      badgeText: 'Schema Catalog',
    },
    {
      title: 'Total Ingested Records',
      value: totalRows > 0 ? totalRows.toLocaleString('en-US') : '0',
      icon: TrendingUp,
      badgeText: 'Live Database',
    },
    {
      title: 'SQL Safety Guard',
      value: 'Read-Only Strict',
      icon: ShieldCheck,
      badgeText: 'AST Validated',
    },
    {
      title: 'Database Engine',
      value: 'SQLite / PostgreSQL',
      icon: Package,
      badgeText: 'Dual Adapter',
    },
  ];

  return (
    <div className="space-y-7 max-w-6xl">
      {/* Welcome Banner */}
      <div className="p-6 md:p-7 bg-white border border-stone-200/90 rounded-xl shadow-card relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-forest-700 bg-sage-50 border border-sage-200/80 px-2.5 py-1 rounded-md">
              <Sparkles className="w-3.5 h-3.5 text-forest-600" />
              <span>Enterprise AI Analytics</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-stone-900 tracking-tight">
              Enterprise AI Text-to-SQL Analytics
            </h2>
            <p className="text-xs md:text-sm text-stone-600 max-w-2xl leading-relaxed">
              Ask questions in plain English, introspect live schemas, upload multi-format CSV datasets,
              and execute validated analytical queries with zero hallucinated tables.
            </p>
          </div>

          <div className="flex flex-wrap md:flex-col gap-2.5 shrink-0">
            <button
              onClick={() => onNavigate('query')}
              className="flex items-center justify-center gap-2 bg-forest-900 hover:bg-forest-850 text-white font-medium text-xs px-4 py-2.5 rounded-lg transition-colors shadow-sm"
            >
              <Terminal className="w-4 h-4 text-emerald-300" />
              <span>Launch Query Workspace</span>
            </button>
            <button
              onClick={() => onNavigate('datasets')}
              className="flex items-center justify-center gap-2 bg-white hover:bg-stone-50 text-stone-700 hover:text-stone-900 text-xs font-medium px-4 py-2.5 rounded-lg border border-stone-200/90 transition-colors shadow-subtle"
            >
              <UploadCloud className="w-4 h-4 text-stone-500" />
              <span>Upload New CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div>
        <div className="flex items-center justify-between mb-3 px-0.5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
            System & Database Metrics
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickStats.map((st) => {
            const Icon = st.icon;
            return (
              <div
                key={st.title}
                className="p-5 bg-white border border-stone-200/90 rounded-xl shadow-card space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-stone-500 font-medium">{st.title}</span>
                  <div className="w-8 h-8 rounded-lg bg-sage-50 text-forest-700 flex items-center justify-center border border-sage-200/80">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div>
                  <p className="text-xl font-bold text-stone-900 font-mono tracking-tight">{st.value}</p>
                  <p className="text-[11px] text-stone-400 mt-0.5">{st.badgeText}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Navigation Cards */}
      <div>
        <div className="flex items-center justify-between mb-3 px-0.5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
            Analytics Capabilities
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            onClick={() => onNavigate('query')}
            className="p-5 bg-white border border-stone-200/90 hover:border-sage-400 hover:shadow-card-hover rounded-xl cursor-pointer transition-all group space-y-2.5"
          >
            <div className="w-9 h-9 rounded-lg bg-sage-50 text-forest-700 flex items-center justify-center border border-sage-200/80">
              <Terminal className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-stone-900 group-hover:text-forest-800 transition-colors flex items-center justify-between">
              <span>Text-to-SQL Engine</span>
              <ArrowRight className="w-4 h-4 text-stone-400 group-hover:text-forest-700 group-hover:translate-x-0.5 transition-all" />
            </h4>
            <p className="text-xs text-stone-500 leading-relaxed">
              Schema-grounded translation of natural language queries with automatic chart generation.
            </p>
          </div>

          <div
            onClick={() => onNavigate('schema')}
            className="p-5 bg-white border border-stone-200/90 hover:border-sage-400 hover:shadow-card-hover rounded-xl cursor-pointer transition-all group space-y-2.5"
          >
            <div className="w-9 h-9 rounded-lg bg-sage-50 text-forest-700 flex items-center justify-center border border-sage-200/80">
              <Database className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-stone-900 group-hover:text-forest-800 transition-colors flex items-center justify-between">
              <span>Schema Introspection</span>
              <ArrowRight className="w-4 h-4 text-stone-400 group-hover:text-forest-700 group-hover:translate-x-0.5 transition-all" />
            </h4>
            <p className="text-xs text-stone-500 leading-relaxed">
              Browse table schemas, inferred column data types, foreign keys, and preview records.
            </p>
          </div>

          <div
            onClick={() => onNavigate('rag')}
            className="p-5 bg-white border border-stone-200/90 hover:border-sage-400 hover:shadow-card-hover rounded-xl cursor-pointer transition-all group space-y-2.5"
          >
            <div className="w-9 h-9 rounded-lg bg-sage-50 text-forest-700 flex items-center justify-center border border-sage-200/80">
              <FileText className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-stone-900 group-hover:text-forest-800 transition-colors flex items-center justify-between">
              <span>Document Intelligence</span>
              <ArrowRight className="w-4 h-4 text-stone-400 group-hover:text-forest-700 group-hover:translate-x-0.5 transition-all" />
            </h4>
            <p className="text-xs text-stone-500 leading-relaxed">
              Upload enterprise policies or reports for grounded RAG QA with strict citations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
