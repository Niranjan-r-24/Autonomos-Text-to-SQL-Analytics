'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Header } from '@/components/Header';
import { QueryInput } from '@/components/QueryInput';
import { QueryResponseCard } from '@/components/QueryResponseCard';
import { SkeletonLoader } from '@/components/SkeletonLoader';
import { SchemaViewerModal } from '@/components/SchemaViewerModal';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { FileUploadModal } from '@/components/FileUploadModal';
import { AlertCircle, Database } from 'lucide-react';
import { API_BASE } from '@/config/api';

export default function Home() {
  const [query, setQuery] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [isExecuting, setIsExecuting] = useState(false);

  // Modals
  const [isSchemaModalOpen, setIsSchemaModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Data & Execution states
  const [schemaData, setSchemaData] = useState<Record<string, any>>({});
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch DB Schema on initial load
  useEffect(() => {
    fetchSchema();
  }, []);

  const fetchSchema = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/schema`);
      if (res.data && res.data.schema) {
        setSchemaData(res.data.schema);
      }
    } catch (err) {
      console.error('Failed to load schema:', err);
    }
  };

  const handleReSeed = async () => {
    try {
      const res = await axios.post(`${API_BASE}/api/seed`);
      if (res.data && res.data.schema) {
        setSchemaData(res.data.schema);
      }
    } catch (err) {
      console.error('Failed to re-seed database:', err);
    }
  };

  const handleUploadSuccess = (tableName: string, updatedSchema: Record<string, any>) => {
    setSchemaData(updatedSchema);
    const targetQuery = `Show first 10 rows from ${tableName}`;
    setQuery(targetQuery);
    setIsUploadModalOpen(false);
    handleRunQuery(targetQuery);
  };

  const handleRunQuery = async (overrideQuery?: string) => {
    const targetQuery = overrideQuery || query;
    if (!targetQuery.trim() || isExecuting) return;

    setIsExecuting(true);
    setErrorMessage(null);

    try {
      const res = await axios.post(`${API_BASE}/api/query`, {
        query: targetQuery.trim(),
        api_key: apiKey,
        provider: provider,
      });

      if (res.data) {
        setPipelineResult(res.data);
        if (!res.data.success && res.data.error) {
          setErrorMessage(res.data.error);
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Query execution failed.';
      setErrorMessage(msg);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleRunCustomSql = async (customSql: string) => {
    if (!customSql.trim() || isExecuting) return;

    setIsExecuting(true);
    setErrorMessage(null);

    try {
      const res = await axios.post(`${API_BASE}/api/execute-sql`, {
        sql: customSql.trim(),
        question: query || 'Custom SQL Execution',
        api_key: apiKey,
        provider: provider,
      });

      if (res.data) {
        if (res.data.success) {
          setPipelineResult((prev: any) => ({
            ...prev,
            sql: customSql,
            rows: res.data.rows,
            columns: res.data.columns,
            row_count: res.data.row_count,
            sql_execution_time_ms: res.data.execution_time_ms,
            explanation: prev?.explanation || 'Executed custom SQL query directly.',
            insights: res.data.insights || prev?.insights,
          }));
        } else {
          setErrorMessage(res.data.error || 'Execution failed.');
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Execution failed.';
      setErrorMessage(msg);
    } finally {
      setIsExecuting(false);
    }
  };

  const tableList = Object.keys(schemaData);

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans text-[#0F172A] selection:bg-[#10B981]/20 selection:text-[#0F172A]">
      {/* 1. Master Header Navigation */}
      <Header
        apiKey={apiKey}
        provider={provider}
        setProvider={setProvider}
        onOpenSchema={() => setIsSchemaModalOpen(true)}
        onOpenApiKeyModal={() => setIsApiKeyModalOpen(true)}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        onReSeed={handleReSeed}
        tableCount={tableList.length || 4}
      />

      {/* Main Container */}
      <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto w-full space-y-6">
        {/* 2. User Query Input Section */}
        <section className="w-full">
          <QueryInput
            query={query}
            setQuery={setQuery}
            onSubmit={handleRunQuery}
            isExecuting={isExecuting}
          />
        </section>

        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="w-full p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs font-semibold flex items-center space-x-3 shadow-xs">
            <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
            <div className="flex-1">
              <span className="font-bold text-rose-800 block text-xs">Security or Execution Notice</span>
              <span className="text-rose-700 leading-relaxed">{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Animated Skeleton Loading State */}
        {isExecuting && (
          <section className="w-full">
            <SkeletonLoader />
          </section>
        )}

        {/* Clean Initial Guidance (Shown before any query has run) */}
        {!pipelineResult && !isExecuting && (
          <section className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-2xl p-6 sm:p-8 text-center space-y-3 shadow-xs">
            <div className="w-10 h-10 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] mx-auto flex items-center justify-center">
              <Database className="w-5 h-5 text-[#10B981]" />
            </div>
            
            <div className="space-y-1 max-w-md mx-auto">
              <h2 className="text-base sm:text-lg font-bold text-[#0F172A] tracking-tight">
                Ask Questions in Natural Language
              </h2>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Type an analytical prompt or pick a sample query above. The system translates intent into secure SQL, generates grounded business insights, and visualizes trends.
              </p>
            </div>
          </section>
        )}

        {/* 3. Unified Query Response Card (Displayed when query results exist) */}
        {pipelineResult && !isExecuting && (
          <section className="w-full">
            <QueryResponseCard
              question={pipelineResult.question || query}
              sql={pipelineResult.sql || ''}
              explanation={pipelineResult.explanation || ''}
              generatedBy={pipelineResult.generated_by}
              insights={pipelineResult.insights}
              rows={pipelineResult.rows || []}
              columns={pipelineResult.columns || []}
              rowCount={pipelineResult.row_count}
              executionTimeSec={pipelineResult.execution_time_sec}
              sqlExecutionTimeMs={pipelineResult.sql_execution_time_ms}
              visualization={pipelineResult.visualization}
              onRunCustomSql={handleRunCustomSql}
              isExecuting={isExecuting}
            />
          </section>
        )}
      </main>

      {/* Database Schema Viewer Modal */}
      <SchemaViewerModal
        schema={schemaData}
        isOpen={isSchemaModalOpen}
        onClose={() => setIsSchemaModalOpen(false)}
        onReSeed={handleReSeed}
      />

      {/* API Key Configuration Modal */}
      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
        apiKey={apiKey}
        setApiKey={setApiKey}
        provider={provider}
        setProvider={setProvider}
      />

      {/* Custom Dataset Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
