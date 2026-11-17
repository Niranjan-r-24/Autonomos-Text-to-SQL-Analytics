'use client';

import React, { useState, useEffect, useRef } from 'react';
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

export interface TableContext {
  tableName: string;
  columns: Array<{ name: string; type: string }>;
  source: 'uploaded' | 'sample';
}

const SAMPLE_TABLE_SET = new Set([
  'customers', 'products', 'orders', 'order_items', 'payments', 'support_tickets', 'sales', 'employees'
]);

export default function Home() {
  const [query, setQuery] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [isExecuting, setIsExecuting] = useState(false);

  // Modals
  const [isSchemaModalOpen, setIsSchemaModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Canonical table-context state & ref
  const [tableContext, setTableContext] = useState<TableContext | null>(null);
  const tableContextRef = useRef<TableContext | null>(null);

  // Data & Execution states
  const [schemaData, setSchemaData] = useState<Record<string, any>>({});
  const [activeTable, setActiveTable] = useState<string | null>(null);
  const activeTableRef = useRef<string | null>(null);
  activeTableRef.current = activeTable;

  const [isSchemaLoading, setIsSchemaLoading] = useState(false);
  const [availableDocuments, setAvailableDocuments] = useState<any[]>([]);
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Request ID guard against out-of-order race conditions
  const activeRequestIdRef = useRef<number>(0);

  // Fetch DB Schema & Document Availability on initial load
  useEffect(() => {
    fetchSchema();
    fetchDocuments();
  }, []);

  const fetchTableContext = async (tableName: string): Promise<TableContext | null> => {
    setIsSchemaLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/schema`, {
        params: { tableName, active_table: tableName }
      });
      const canonicalName = res.data?.tableName || tableName;
      const schemaEntry = res.data?.schema?.[canonicalName];
      if (schemaEntry && schemaEntry.columns) {
        const ctx: TableContext = {
          tableName: canonicalName,
          columns: schemaEntry.columns.map((col: any) => ({
            name: col.name,
            type: col.type || 'TEXT',
          })),
          source: SAMPLE_TABLE_SET.has(canonicalName.toLowerCase()) ? 'sample' : 'uploaded',
        };
        setTableContext(ctx);
        tableContextRef.current = ctx;
        setActiveTable(canonicalName);
        activeTableRef.current = canonicalName;
        setSchemaData((prev) => ({ ...prev, [canonicalName]: schemaEntry }));
        return ctx;
      }
      return null;
    } catch (err: any) {
      console.error('Failed to load table context:', err);
      const data = err.response?.data;
      const msg = (data && (data.detail?.message || data.detail || data.message)) || `Failed to load schema for ${tableName}.`;
      setErrorMessage(msg);
      return null;
    } finally {
      setIsSchemaLoading(false);
    }
  };

  const fetchSchema = async (selectedTable?: string | null) => {
    setIsSchemaLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/schema`);
      if (res.data && res.data.schema) {
        const filtered: Record<string, any> = {};
        for (const [k, v] of Object.entries(res.data.schema)) {
          if (!['audit_logs', 'sqlite_sequence'].includes(k.toLowerCase())) {
            filtered[k] = v;
          }
        }
        setSchemaData(filtered);

        const target = selectedTable || activeTableRef.current;
        if (target && filtered[target]) {
          await fetchTableContext(target);
        } else if (!tableContextRef.current && Object.keys(filtered).length > 0) {
          const defaultTable = Object.keys(filtered)[0];
          await fetchTableContext(defaultTable);
        }
      }
    } catch (err: any) {
      console.error('Failed to load schema:', err);
      const data = err.response?.data;
      const msg = (data && (data.detail?.message || data.detail || data.message)) || 'Failed to load schema.';
      setErrorMessage(msg);
    } finally {
      setIsSchemaLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/documents`);
      if (res.data && res.data.documents) {
        setAvailableDocuments(res.data.documents);
      }
    } catch (err) {
      try {
        const res2 = await axios.get(`${API_BASE}/api/rag/documents`);
        if (res2.data && res2.data.documents) {
          setAvailableDocuments(res2.data.documents);
        }
      } catch (err2) {
        console.warn('Documents feature unavailable:', err2);
      }
    }
  };

  const handleQueryDocument = (docName: string) => {
    const targetQuery = `According to the document ${docName}, what are the key requirements and details?`;
    setQuery(targetQuery);
    setIsUploadModalOpen(false);
    handleRunQuery(targetQuery);
  };

  const handleReSeed = async () => {
    try {
      const res = await axios.post(`${API_BASE}/api/seed`);
      if (res.data && res.data.schema) {
        setSchemaData(res.data.schema);
        setTableContext(null);
        tableContextRef.current = null;
        setActiveTable(null);
        activeTableRef.current = null;
        setPipelineResult(null);
        setErrorMessage(null);
        const keys = Object.keys(res.data.schema);
        if (keys.length > 0) {
          await fetchTableContext(keys[0]);
        }
      }
    } catch (err) {
      console.error('Failed to re-seed database:', err);
    }
  };

  const handleUploadSuccess = async (tableName: string, updatedSchema: Record<string, any>) => {
    fetchDocuments();
    setPipelineResult(null);
    setErrorMessage(null);
    setQuery('');

    if (tableName && tableName !== 'knowledge_base' && !['audit_logs', 'sqlite_sequence'].includes(tableName.toLowerCase())) {
      await fetchTableContext(tableName);
    }
  };

  const handleSelectTable = async (tableName: string | null) => {
    setPipelineResult(null);
    setErrorMessage(null);
    setQuery('');

    if (!tableName || ['audit_logs', 'sqlite_sequence'].includes(tableName.toLowerCase())) {
      setTableContext(null);
      tableContextRef.current = null;
      setActiveTable(null);
      activeTableRef.current = null;
      return;
    }
    await fetchTableContext(tableName);
  };

  const isTableSchemaReady = Boolean(tableContext?.columns?.length) && !isSchemaLoading;

  const handleRunQuery = async (overrideQuery?: string, overrideTable?: string) => {
    const targetQuery = overrideQuery || query;
    if (!targetQuery.trim()) return;
    if (isExecuting && !overrideQuery) return;

    let currentContext = tableContextRef.current;
    if (overrideTable && (!currentContext || currentContext.tableName !== overrideTable)) {
      currentContext = await fetchTableContext(overrideTable);
    }

    if (!currentContext) {
      setErrorMessage("Please select a table from the dataset bar above to query.");
      return;
    }

    if (isSchemaLoading) {
      return;
    }

    const currentRequestId = ++activeRequestIdRef.current;
    setIsExecuting(true);
    setErrorMessage(null);
    setPipelineResult(null);

    try {
      const res = await axios.post(`${API_BASE}/api/query`, {
        question: targetQuery.trim(),
        query: targetQuery.trim(),
        tableName: currentContext.tableName,
        active_table: currentContext.tableName,
        table_name: currentContext.tableName,
        schema: currentContext.columns,
        api_key: apiKey,
        provider: provider,
      });

      if (currentRequestId !== activeRequestIdRef.current) return;

      if (res.data) {
        if (!res.data.success && res.data.error) {
          setErrorMessage(res.data.error);
          setPipelineResult(null);
        } else {
          setPipelineResult({ ...res.data, _reqId: currentRequestId });
          setErrorMessage(null);
        }
      }
    } catch (err: any) {
      if (currentRequestId !== activeRequestIdRef.current) return;
      const data = err.response?.data;
      let msg = 'Query execution failed.';
      if (data) {
        if (typeof data.detail === 'object' && data.detail !== null) {
          msg = data.detail.message || JSON.stringify(data.detail);
        } else if (typeof data.detail === 'string') {
          msg = data.detail;
        } else if (data.message) {
          msg = data.message;
        } else if (data.error) {
          msg = data.error;
        }
      } else if (err.message) {
        msg = err.message;
      }
      setErrorMessage(msg);
      setPipelineResult(null);
    } finally {
      if (currentRequestId === activeRequestIdRef.current) {
        setIsExecuting(false);
      }
    }
  };

  const handleRunCustomSql = async (customSql: string) => {
    if (!customSql.trim() || isExecuting) return;

    const currentContext = tableContextRef.current;
    if (!currentContext) {
      setErrorMessage("Please select an active table before executing SQL.");
      return;
    }

    const currentRequestId = ++activeRequestIdRef.current;
    setIsExecuting(true);
    setErrorMessage(null);

    try {
      const res = await axios.post(`${API_BASE}/api/execute-sql`, {
        sql: customSql.trim(),
        question: query || 'Custom SQL Execution',
        tableName: currentContext.tableName,
        active_table: currentContext.tableName,
        table_name: currentContext.tableName,
        schema: currentContext.columns,
        api_key: apiKey,
        provider: provider,
      });

      if (currentRequestId !== activeRequestIdRef.current) return;

      if (res.data) {
        if (res.data.success) {
          setPipelineResult((prev: any) => ({
            ...prev,
            _reqId: currentRequestId,
            sql: customSql,
            rows: res.data.rows,
            columns: res.data.columns,
            row_count: res.data.row_count,
            sql_execution_time_ms: res.data.execution_time_ms,
            explanation: prev?.explanation || 'Executed custom SQL query directly.',
            insights: res.data.insights || prev?.insights,
            visualization: res.data.visualization || prev?.visualization,
          }));
          setErrorMessage(null);
        } else {
          setErrorMessage(res.data.error || 'Execution failed.');
        }
      }
    } catch (err: any) {
      if (currentRequestId !== activeRequestIdRef.current) return;
      const data = err.response?.data;
      let msg = 'Execution failed.';
      if (data) {
        if (typeof data.detail === 'object' && data.detail !== null) {
          msg = data.detail.message || JSON.stringify(data.detail);
        } else if (typeof data.detail === 'string') {
          msg = data.detail;
        } else if (data.message) {
          msg = data.message;
        } else if (data.error) {
          msg = data.error;
        }
      } else if (err.message) {
        msg = err.message;
      }
      setErrorMessage(msg);
    } finally {
      if (currentRequestId === activeRequestIdRef.current) {
        setIsExecuting(false);
      }
    }
  };

  const tableList = Object.keys(schemaData).filter(
    (t) => !['audit_logs', 'sqlite_sequence'].includes(t.toLowerCase())
  );

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
        docCount={availableDocuments.length}
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
            activeTable={tableContext?.tableName || activeTable}
            tables={tableList}
            tableColumns={tableContext?.columns ? tableContext.columns.map((c) => c.name) : (activeTable && schemaData[activeTable]?.columns ? schemaData[activeTable].columns.map((c: any) => c.name) : [])}
            onSelectTable={handleSelectTable}
            isTableSchemaReady={isTableSchemaReady}
            isSchemaLoading={isSchemaLoading}
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
              key={`query-card-${pipelineResult._reqId || 0}-${pipelineResult.sql}-${pipelineResult.rows?.length}-${pipelineResult.columns?.join(',')}`}
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
              route={pipelineResult.route}
              citations={pipelineResult.citations}
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
        onSelectTable={handleSelectTable}
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

      {/* Custom Dataset & Document Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        onQueryDocument={handleQueryDocument}
      />
    </div>
  );
}
