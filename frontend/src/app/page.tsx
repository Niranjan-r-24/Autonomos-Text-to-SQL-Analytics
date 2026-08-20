'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Header } from '@/components/Header';
import { QueryInput } from '@/components/QueryInput';
import { SqlViewer } from '@/components/SqlViewer';
import { QueryExplanation } from '@/components/QueryExplanation';
import { DataVisualization } from '@/components/DataVisualization';
import { SchemaViewerModal } from '@/components/SchemaViewerModal';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { FileUploadModal } from '@/components/FileUploadModal';
import { AlertCircle, Database, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';
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

  return (
    <div className="min-h-screen bg-clay-100 flex flex-col font-sans text-slate-900 selection:bg-lime-300">
      {/* 1. Header & Database Connection */}
      <Header
        apiKey={apiKey}
        provider={provider}
        setProvider={setProvider}
        onOpenSchema={() => setIsSchemaModalOpen(true)}
        onOpenApiKeyModal={() => setIsApiKeyModalOpen(true)}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        onReSeed={handleReSeed}
      />

      {/* Main Container */}
      <main className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full space-y-6">
        {/* 2. User Question Input */}
        <section className="w-full">
          <QueryInput
            query={query}
            setQuery={setQuery}
            onSubmit={handleRunQuery}
            isExecuting={isExecuting}
            onOpenSchema={() => setIsSchemaModalOpen(true)}
          />
        </section>

        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="w-full p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs font-semibold flex items-center space-x-3 shadow-sm">
            <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
            <div>
              <span className="font-extrabold block">Query Error</span>
              <span className="text-rose-700">{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Initial Welcome / Quick Start Card (when no query has been run yet) */}
        {!pipelineResult && !isExecuting && (
          <section className="clay-card p-8 bg-white border border-slate-200 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-lime-100 text-slate-900 mx-auto flex items-center justify-center">
              <Database className="w-6 h-6 text-lime-600" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-slate-900">
                Ready to Query Your Database
              </h2>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                Type any analytical question in plain English above or choose a sample prompt to generate SQL, view explanations, and explore charts.
              </p>
            </div>
            <div className="pt-2 flex flex-wrap justify-center gap-2">
              {[
                'Top 5 revenue products',
                'Monthly sales trend by region',
                'Customer distribution by plan & country',
              ].map((sample) => (
                <button
                  key={sample}
                  onClick={() => {
                    setQuery(sample);
                    handleRunQuery(sample);
                  }}
                  className="px-4 py-2 rounded-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-800 transition-all flex items-center space-x-1.5"
                >
                  <span>{sample}</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                </button>
              ))}
            </div>
          </section>
        )}

        {/* 3. Query Explanation */}
        {pipelineResult?.explanation && (
          <section className="w-full">
            <QueryExplanation
              explanation={pipelineResult.explanation}
              generatedBy={pipelineResult.generated_by}
            />
          </section>
        )}

        {/* 4. Generated SQL Viewer */}
        {pipelineResult?.sql && (
          <section className="w-full">
            <SqlViewer
              sql={pipelineResult.sql}
              onRunCustomSql={handleRunCustomSql}
              isExecuting={isExecuting}
            />
          </section>
        )}

        {/* 5. Query Results (Data Table & Charts) */}
        {pipelineResult?.success && pipelineResult.rows && (
          <section className="w-full">
            <DataVisualization
              rows={pipelineResult.rows}
              columns={pipelineResult.columns || []}
              recommendedChartType={pipelineResult.visualization?.chart_type}
              xAxisKey={pipelineResult.visualization?.x_axis}
              yAxisKeys={pipelineResult.visualization?.y_axes}
              title={pipelineResult.visualization?.title}
              executionTimeSec={pipelineResult.execution_time_sec}
              sqlExecutionTimeMs={pipelineResult.sql_execution_time_ms}
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
