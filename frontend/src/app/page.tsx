'use client';

import React, { useState, useEffect } from 'react';
import { Sidebar, NavTab } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { Overview } from '@/components/Overview';
import { QueryWorkspace } from '@/components/QueryWorkspace';
import { SchemaExplorer } from '@/components/SchemaExplorer';
import { DatasetManager } from '@/components/DatasetManager';
import { RagWorkspace } from '@/components/RagWorkspace';
import { HistoryWorkspace } from '@/components/HistoryWorkspace';
import { SettingsModal } from '@/components/SettingsModal';
import { fetchSchema, seedDatabase } from '@/lib/api';
import { SchemaInfo, QueryResult } from '@/types';

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [schema, setSchema] = useState<SchemaInfo | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Settings & Provider
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [provider, setProvider] = useState<string>('gemini');
  const [apiKey, setApiKey] = useState<string>('');

  // Initial query state when navigating from schema or history
  const [currentQuery, setCurrentQuery] = useState<string>('');

  const loadSchema = async (refresh: boolean = false) => {
    setIsRefreshing(true);
    try {
      const data = await fetchSchema(refresh);
      if (data && typeof data === 'object' && data.tables) {
        setSchema(data);
      } else {
        setSchema({ status: 'ok', tables: {}, table_names: [], relationships: [] });
      }
    } catch (err) {
      console.error('Failed to load schema:', err);
      setSchema({ status: 'error', tables: {}, table_names: [], relationships: [] });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleReseed = async () => {
    setIsRefreshing(true);
    try {
      await seedDatabase(true);
      await loadSchema(true);
    } catch (err) {
      console.error('Failed to reseed database:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleSaveSettings = (newProvider: string, newApiKey: string) => {
    setProvider(newProvider);
    if (newApiKey) {
      setApiKey(newApiKey);
    }
    if (typeof window !== 'undefined') {
      localStorage.setItem('autonomos_provider', newProvider);
      if (newApiKey) {
        localStorage.setItem('autonomos_api_key', newApiKey);
      }
    }
  };

  const handleNavigateToQuery = (q: string) => {
    setCurrentQuery(q);
    setActiveTab('query');
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedProvider = localStorage.getItem('autonomos_provider');
        const savedKey = localStorage.getItem('autonomos_api_key');
        if (savedProvider) setProvider(savedProvider);
        if (savedKey) setApiKey(savedKey);
      } catch (e) {
        console.warn('localStorage read error:', e);
      }
    }
    loadSchema(false);
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        tableCount={schema?.table_names?.length || 0}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          onRefreshSchema={() => loadSchema(true)}
          onReseedData={handleReseed}
          onOpenSettings={() => setIsSettingsOpen(true)}
          tableCount={schema?.table_names?.length || 0}
          provider={provider}
          isRefreshing={isRefreshing}
        />

        {/* Tab View Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'overview' && (
            <Overview
              schema={schema}
              onNavigate={setActiveTab}
              onRunQuickQuery={handleNavigateToQuery}
            />
          )}

          {activeTab === 'query' && (
            <QueryWorkspace
              onSuccessQuery={() => {}}
              provider={provider}
              apiKey={apiKey}
              initialQuery={currentQuery}
            />
          )}

          {activeTab === 'schema' && (
            <SchemaExplorer
              schema={schema}
              onRefresh={() => loadSchema(true)}
              onSelectTableForQuery={handleNavigateToQuery}
              isRefreshing={isRefreshing}
            />
          )}

          {activeTab === 'datasets' && (
            <DatasetManager
              onDatasetUploaded={() => loadSchema(true)}
              onNavigateToQuery={handleNavigateToQuery}
            />
          )}

          {activeTab === 'rag' && <RagWorkspace />}

          {activeTab === 'history' && (
            <HistoryWorkspace onRerunQuery={handleNavigateToQuery} />
          )}

          {activeTab === 'settings' && (
            <div className="max-w-xl">
              <h2 className="text-base font-semibold text-slate-100 mb-4">
                Configuration & API Keys
              </h2>
              <button
                onClick={() => setIsSettingsOpen(true)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors"
              >
                Open Settings Panel
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentProvider={provider}
        onSaveProvider={handleSaveSettings}
      />
    </div>
  );
}
