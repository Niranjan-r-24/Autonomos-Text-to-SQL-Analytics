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
import { fetchSchema, fetchDatasets, seedDatabase } from '@/lib/api';
import { SchemaInfo, DatasetMetadata } from '@/types';

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [schema, setSchema] = useState<SchemaInfo | null>(null);
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetMetadata | null>(null);
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
      const [schemaData, datasetsData] = await Promise.all([
        fetchSchema(refresh),
        fetchDatasets()
      ]);

      if (schemaData && typeof schemaData === 'object' && schemaData.tables) {
        setSchema(schemaData);
      } else {
        setSchema({ status: 'ok', tables: {}, table_names: [], relationships: [] });
      }

      if (Array.isArray(datasetsData)) {
        setDatasets(datasetsData);
      } else if (schemaData?.datasets) {
        setDatasets(schemaData.datasets);
      }
    } catch (err) {
      console.error('Failed to load schema and datasets:', err);
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

  const handleNavigateToQuery = (q: string, ds?: DatasetMetadata | null) => {
    setCurrentQuery(q);
    if (ds) {
      setSelectedDataset(ds);
    } else {
      // Find matching dataset from question
      for (const d of datasets) {
        if (q.toLowerCase().includes(d.table_name.toLowerCase())) {
          setSelectedDataset(d);
          break;
        }
      }
    }
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

  const totalActiveTables = Math.max(
    schema?.table_names?.length || 0,
    datasets.length
  );

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        tableCount={totalActiveTables}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          onRefreshSchema={() => loadSchema(true)}
          onReseedData={handleReseed}
          onOpenSettings={() => setIsSettingsOpen(true)}
          tableCount={totalActiveTables}
          provider={provider}
          isRefreshing={isRefreshing}
        />

        {/* Tab View Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'overview' && (
            <Overview
              schema={schema}
              onNavigate={setActiveTab}
              onRunQuickQuery={(q) => handleNavigateToQuery(q)}
            />
          )}

          {activeTab === 'query' && (
            <QueryWorkspace
              onSuccessQuery={() => {}}
              provider={provider}
              apiKey={apiKey}
              initialQuery={currentQuery}
              datasets={datasets}
              activeDataset={selectedDataset}
              onSelectDataset={setSelectedDataset}
            />
          )}

          {activeTab === 'schema' && (
            <SchemaExplorer
              schema={schema}
              onRefresh={() => loadSchema(true)}
              onSelectTableForQuery={(q) => handleNavigateToQuery(q)}
              isRefreshing={isRefreshing}
            />
          )}

          {activeTab === 'datasets' && (
            <DatasetManager
              onDatasetUploaded={(res?: any) => {
                if (res?.datasetId || res?.tableName || res?.dataset?.table_name) {
                  const tbl = res.tableName || res.table_name || res.dataset?.table_name;
                  const did = res.datasetId || res.dataset_id || res.dataset?.dataset_id;
                  const newDs: DatasetMetadata = {
                    dataset_id: did || `ds_${tbl}`,
                    datasetId: did || `ds_${tbl}`,
                    table_name: tbl,
                    tableName: tbl,
                    source_file_name: res.source_file_name || res.filename || `${tbl}.csv`,
                    columns_json: res.columns_json || JSON.stringify(res.columns || []),
                    columns: res.columns || res.dataset?.columns || [],
                    row_count: res.row_count ?? res.dataset?.row_count ?? 0,
                    created_at: new Date().toISOString()
                  };
                  setSelectedDataset(newDs);
                }
                loadSchema(true);
              }}
              onNavigateToQuery={(q) => handleNavigateToQuery(q, selectedDataset)}
              onNavigateToSchema={() => setActiveTab('schema')}
            />
          )}

          {activeTab === 'rag' && (
            <RagWorkspace
              onDocumentUploaded={(newSchema?: SchemaInfo) => {
                if (newSchema && newSchema.tables) {
                  setSchema(newSchema);
                } else {
                  loadSchema(true);
                }
              }}
              onNavigateToSchema={() => setActiveTab('schema')}
            />
          )}

          {activeTab === 'history' && (
            <HistoryWorkspace onRerunQuery={(q) => handleNavigateToQuery(q)} />
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
