'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Image from 'next/image';
import { Header } from '@/components/Header';
import { Sidebar, AgentStep } from '@/components/Sidebar';
import { QueryInput } from '@/components/QueryInput';
import { AgentThoughtStream } from '@/components/AgentThoughtStream';
import { SqlViewer } from '@/components/SqlViewer';
import { DataVisualization } from '@/components/DataVisualization';
import { SchemaViewerModal } from '@/components/SchemaViewerModal';
import { FileUploadModal } from '@/components/FileUploadModal';
import { KnowledgeBaseModal } from '@/components/KnowledgeBaseModal';
import {
  Sparkles, AlertCircle, ArrowUpRight, Bot, ShieldCheck, Zap, Key, Database,
  BarChart2, Code2, Sliders, Wrench, CheckCircle2, Clock, RefreshCw, Activity, Loader2
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

export default function Home() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'analytics' | 'pulse'>('dashboard');
  const [query, setQuery] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [isSchemaModalOpen, setIsSchemaModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isKnowledgeModalOpen, setIsKnowledgeModalOpen] = useState(false);

  // API Key Verification state
  const [isVerifyingKey, setIsVerifyingKey] = useState(false);
  const [keyVerifyResult, setKeyVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);

  // Pipeline execution state
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // DB Schema State
  const [schemaData, setSchemaData] = useState<Record<string, any>>({});

  // Fetch Schema on Mount
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
      await axios.post(`${API_BASE}/api/seed`);
      await fetchSchema();
    } catch (err) {
      console.error('Failed to re-seed database:', err);
    }
  };

  const handleVerifyApiKey = async () => {
    setIsVerifyingKey(true);
    setKeyVerifyResult(null);

    try {
      const res = await axios.post(`${API_BASE}/api/verify-key`, {
        api_key: apiKey,
        provider: provider,
      });

      if (res.data) {
        setKeyVerifyResult({
          valid: res.data.valid,
          message: res.data.message,
        });
      }
    } catch (err: any) {
      setKeyVerifyResult({
        valid: false,
        message: err.response?.data?.detail || err.message || 'API key verification error.',
      });
    } finally {
      setIsVerifyingKey(false);
    }
  };

  const handleUploadSuccess = (tableName: string, updatedSchema: Record<string, any>) => {
    setSchemaData(updatedSchema);
    const targetQuery = `SELECT * FROM ${tableName} LIMIT 10;`;
    setQuery(targetQuery);
    setActiveTab('dashboard');
    handleRunPipeline(targetQuery);
  };

  const handleRunPipeline = async (overrideQuery?: string) => {
    const targetQuery = overrideQuery || query;
    if (!targetQuery.trim() || isPipelineRunning) return;

    setIsPipelineRunning(true);
    setErrorMessage(null);

    // Reset agent steps to pending
    const initialSteps: AgentStep[] = [
      { agent_id: 'schema_linker', agent_name: 'Schema Linker Agent', status: 'RUNNING' },
      { agent_id: 'sql_generator', agent_name: 'SQL Generator Agent', status: 'PENDING' },
      { agent_id: 'self_corrector', agent_name: 'Self-Correction Agent', status: 'PENDING' },
      { agent_id: 'visualizer', agent_name: 'Visualization Agent', status: 'PENDING' },
    ];
    setAgentSteps(initialSteps);

    try {
      const res = await axios.post(`${API_BASE}/api/query`, {
        query: targetQuery,
        api_key: apiKey,
        provider: provider,
      });

      if (res.data) {
        setPipelineResult(res.data);
        if (res.data.agent_steps) {
          setAgentSteps(res.data.agent_steps);
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Pipeline execution failed.';
      setErrorMessage(msg);
      setAgentSteps((prev) =>
        prev.map((s) => ({ ...s, status: s.status === 'RUNNING' ? 'FAILED' : s.status }))
      );
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const handleRunCustomSql = async (customSql: string) => {
    handleRunPipeline(query);
  };

  return (
    <div className="min-h-screen bg-clay-100 flex flex-col font-sans text-slate-900 selection:bg-lime-300">
      {/* Top Header Navigation */}
      <Header
        activeTab={activeTab}
        setActiveTab={(tab: any) => setActiveTab(tab)}
        apiKey={apiKey}
        setApiKey={setApiKey}
        provider={provider}
        setProvider={setProvider}
        onOpenSchema={() => setIsSchemaModalOpen(true)}
        onOpenApiKeyModal={() => setIsApiKeyModalOpen(true)}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        onOpenKnowledgeModal={() => setIsKnowledgeModalOpen(true)}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Floating Icon Pillar & Agent Workflow Drawer */}
        <Sidebar
          agentSteps={agentSteps}
          isPipelineRunning={isPipelineRunning}
        />

        {/* Main Canvas Dashboard Content */}
        <main className="flex-1 p-8 overflow-y-auto space-y-7 max-w-7xl mx-auto">
          {activeTab === 'dashboard' && (
            <>
              {/* Header Title & Natural Language Search Bar Canvas */}
              <section className="w-full">
                <QueryInput
                  query={query}
                  setQuery={setQuery}
                  onSubmit={handleRunPipeline}
                  isPipelineRunning={isPipelineRunning}
                />
              </section>

              {/* Error Banner if any */}
              {errorMessage && (
                <div className="w-full p-4 rounded-3xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center space-x-3 shadow-sm">
                  <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
                  <div>
                    <span className="font-extrabold">Notice:</span> {errorMessage}
                  </div>
                </div>
              )}

              {/* Banner Hero Widget */}
              {!pipelineResult && !isPipelineRunning && (
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* 3D Banner Card */}
                  <div className="lg:col-span-1 clay-card p-6 relative overflow-hidden flex flex-col justify-between min-h-[300px] bg-slate-900 text-white shadow-xl">
                    <div className="absolute inset-0 opacity-40 mix-blend-overlay">
                      <Image
                        src="/lime_3d_banner.jpg"
                        alt="Orvion 3D Graphic"
                        fill
                        className="object-cover"
                      />
                    </div>

                    <div className="relative z-10 space-y-2">
                      <span className="px-3 py-1 rounded-full bg-lime-400 text-slate-900 text-[11px] font-extrabold inline-block">
                        Pro Version
                      </span>
                      <h3 className="text-xl font-extrabold tracking-tight">
                        Orvion Text-to-SQL AI
                      </h3>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        Humanized multi-agent architecture with self-healing SQL execution & dynamic charts.
                      </p>
                    </div>

                    <div className="relative z-10 pt-6 flex items-center justify-between border-t border-slate-700/60">
                      <div>
                        <div className="text-2xl font-extrabold text-lime-400">30-45%</div>
                        <div className="text-[10px] text-slate-400 font-bold uppercase">Accuracy Boost</div>
                      </div>
                      <div>
                        <div className="text-2xl font-extrabold text-white">12-21s</div>
                        <div className="text-[10px] text-slate-400 font-bold uppercase">Avg Query Speed</div>
                      </div>
                    </div>
                  </div>

                  {/* Default Executive Analytics Preview Widgets */}
                  <div className="lg:col-span-2 clay-card p-8 flex flex-col justify-between bg-white relative">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center space-x-2 text-xs font-bold text-slate-500 mb-1">
                          <Zap className="w-3.5 h-3.5 text-lime-500 animate-pulse" />
                          <span>Ready to Analyze</span>
                        </div>
                        <h2 className="text-xl font-extrabold text-slate-900">
                          Enterprise Analytics Dashboard
                        </h2>
                      </div>
                      <button
                        onClick={() => handleRunPipeline("Top 5 revenue products")}
                        className="flex items-center space-x-2 px-5 py-2.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 text-xs font-extrabold shadow-sm transition-all"
                      >
                        <span>Run Sample Analysis</span>
                        <ArrowUpRight className="w-4 h-4 text-lime-400" />
                      </button>
                    </div>

                    <div className="grid grid-cols-3 gap-4 pt-6">
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-1">
                        <span className="text-[10px] font-bold uppercase text-slate-400">Total Sales</span>
                        <div className="text-xl font-extrabold text-slate-900">$29.48m</div>
                        <span className="text-[10px] font-bold text-lime-600 bg-lime-100 px-2 py-0.5 rounded-full inline-block">
                          +14.2% YoY
                        </span>
                      </div>

                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-1">
                        <span className="text-[10px] font-bold uppercase text-slate-400">Activity Count</span>
                        <div className="text-xl font-extrabold text-slate-900">186</div>
                        <span className="text-[10px] font-bold text-slate-600 bg-slate-200 px-2 py-0.5 rounded-full inline-block">
                          Active This Week
                        </span>
                      </div>

                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-1">
                        <span className="text-[10px] font-bold uppercase text-slate-400">Total Spend</span>
                        <div className="text-xl font-extrabold text-slate-900">$278.86</div>
                        <span className="text-[10px] font-bold text-lime-600 bg-lime-100 px-2 py-0.5 rounded-full inline-block">
                          Optimized
                        </span>
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {/* Real-time Agent Execution Stream */}
              {agentSteps.length > 0 && (
                <section className="w-full">
                  <AgentThoughtStream
                    agentSteps={agentSteps}
                    totalTimeSec={pipelineResult?.total_execution_time_sec}
                  />
                </section>
              )}

              {/* Generated SQL Code Viewer */}
              {pipelineResult?.sql && (
                <section className="w-full">
                  <SqlViewer
                    sql={pipelineResult.sql}
                    onRunCustomSql={handleRunCustomSql}
                    isPipelineRunning={isPipelineRunning}
                  />
                </section>
              )}

              {pipelineResult?.route === 'rag' && (
                <section className="clay-card bg-white p-6 space-y-4">
                  <div><span className="text-[10px] font-extrabold uppercase tracking-wider text-lime-700">Document intelligence</span><h2 className="text-lg font-extrabold text-slate-900 mt-1">Executive Summary</h2><p className="text-sm leading-relaxed text-slate-700 mt-2">{pipelineResult.answer}</p></div>
                  <div className="border-t border-slate-100 pt-4"><h3 className="text-xs font-extrabold text-slate-700 mb-2">Citations</h3><div className="space-y-2">{(pipelineResult.citations || []).map((citation: any, index: number) => <div key={index} className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600"><span className="font-bold text-slate-800">[{index + 1}] {citation.source}, chunk {citation.chunk}</span><p className="mt-1">{citation.excerpt}</p></div>)}</div></div>
                </section>
              )}

              {/* Multi-Widget Executive Data Visualization Canvas */}
              {pipelineResult && (
                <section className="w-full">
                  <DataVisualization
                    rows={pipelineResult.rows || []}
                    columns={pipelineResult.columns || []}
                    recommendedChartType={pipelineResult.visualization?.chart_type}
                    xAxisKey={pipelineResult.visualization?.x_axis}
                    yAxisKeys={pipelineResult.visualization?.y_axes}
                    title={pipelineResult.visualization?.title}
                  />
                </section>
              )}
            </>
          )}

          {activeTab === 'analytics' && (
            <div className="space-y-6">
              {/* Analytics Header */}
              <div className="clay-card p-6 bg-white flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 mb-1">
                    <BarChart2 className="w-4 h-4 text-lime-500" />
                    <span>Analytics Workspace</span>
                  </div>
                  <h1 className="text-2xl font-extrabold text-slate-900">
                    Enterprise Data & Visual Analytics
                  </h1>
                  <p className="text-xs text-slate-500 mt-1">
                    Multi-dimensional chart widgets, tabular data inspection, and raw query output.
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleRunPipeline("Top 5 revenue products")}
                    className="px-4 py-2 rounded-full bg-slate-900 text-white hover:bg-slate-800 text-xs font-bold transition-all"
                  >
                    Run Sample Revenue Query
                  </button>
                  <button
                    onClick={() => setIsSchemaModalOpen(true)}
                    className="px-4 py-2 rounded-full bg-lime-400 text-slate-900 hover:bg-lime-300 text-xs font-extrabold transition-all"
                  >
                    Explore DB Schema
                  </button>
                </div>
              </div>

              {/* Data Visualization Canvas */}
              {pipelineResult ? (
                <DataVisualization
                  rows={pipelineResult.rows || []}
                  columns={pipelineResult.columns || []}
                  recommendedChartType={pipelineResult.visualization?.chart_type}
                  xAxisKey={pipelineResult.visualization?.x_axis}
                  yAxisKeys={pipelineResult.visualization?.y_axes}
                  title={pipelineResult.visualization?.title}
                />
              ) : (
                <div className="clay-card p-10 bg-white text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-lime-100 text-slate-900 mx-auto flex items-center justify-center">
                    <BarChart2 className="w-6 h-6 text-lime-600" />
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold text-slate-900">No Analytics Loaded</h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                      Run a query prompt from the search bar or pick a sample prompt below to generate dynamic interactive analytics.
                    </p>
                  </div>

                  <div className="flex flex-wrap justify-center gap-2 pt-2">
                    {["Top 5 revenue products", "Monthly sales trend by region", "Customer distribution by plan & country"].map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => {
                          setQuery(prompt);
                          setActiveTab('dashboard');
                          handleRunPipeline(prompt);
                        }}
                        className="px-4 py-2 rounded-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-800 transition-all"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'pulse' && (
            <div className="space-y-6">
              {/* AI Pulse Header */}
              <div className="clay-card p-6 bg-slate-900 text-white flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2 text-xs font-semibold text-lime-400 mb-1">
                    <Sparkles className="w-4 h-4 animate-pulse" />
                    <span>Multi-Agent Engine</span>
                  </div>
                  <h1 className="text-2xl font-extrabold tracking-tight">
                    AI Pipeline Pulse & Agent Diagnostics
                  </h1>
                  <p className="text-xs text-slate-300 mt-1">
                    4-Stage Agent Architecture: Schema Linker → SQL Generator → Self-Corrector → Data Visualizer
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-3 py-1 rounded-full bg-lime-400/20 text-lime-300 text-xs font-bold border border-lime-400/30 flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-lime-400" />
                    Engine Active
                  </span>
                </div>
              </div>

              {/* Agent Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  {
                    id: 'schema_linker',
                    name: 'Schema Linker Agent',
                    desc: 'Filters enterprise schema to relevant tables & columns.',
                    icon: Database,
                    status: agentSteps.find((s) => s.agent_id === 'schema_linker')?.status || 'PENDING',
                  },
                  {
                    id: 'sql_generator',
                    name: 'SQL Generator Agent',
                    desc: 'Formulates ANSI SQL with clean JOINs and aggregations.',
                    icon: Code2,
                    status: agentSteps.find((s) => s.agent_id === 'sql_generator')?.status || 'PENDING',
                  },
                  {
                    id: 'self_corrector',
                    name: 'Self-Corrector Agent',
                    desc: 'Executes query and auto-heals up to 3 SQL tracebacks.',
                    icon: Wrench,
                    status: agentSteps.find((s) => s.agent_id === 'self_corrector')?.status || 'PENDING',
                  },
                  {
                    id: 'visualizer',
                    name: 'Visualization Agent',
                    desc: 'Infers data shapes to choose optimal Recharts UI.',
                    icon: BarChart2,
                    status: agentSteps.find((s) => s.agent_id === 'visualizer')?.status || 'PENDING',
                  },
                ].map((agent) => {
                  const AgentIcon = agent.icon;
                  const isCompleted = agent.status === 'COMPLETED';
                  const isRunning = agent.status === 'RUNNING';

                  return (
                    <div key={agent.id} className="clay-card p-5 bg-white space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center">
                          <AgentIcon className="w-4 h-4 text-lime-400" />
                        </div>
                        <span
                          className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase ${
                            isCompleted
                              ? 'bg-lime-100 text-lime-800'
                              : isRunning
                              ? 'bg-amber-100 text-amber-800 animate-pulse'
                              : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {agent.status}
                        </span>
                      </div>

                      <div>
                        <h3 className="text-sm font-extrabold text-slate-900">{agent.name}</h3>
                        <p className="text-xs text-slate-500 mt-1 leading-relaxed">{agent.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Agent Thought Stream */}
              {agentSteps.length > 0 ? (
                <AgentThoughtStream
                  agentSteps={agentSteps}
                  totalTimeSec={pipelineResult?.total_execution_time_sec}
                />
              ) : (
                <div className="clay-card p-8 bg-white text-center">
                  <p className="text-xs text-slate-500">
                    No pipeline execution history recorded yet. Execute a search query to view real-time agent thought logs.
                  </p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Enterprise Schema Inspector Modal */}
      <SchemaViewerModal
        schema={schemaData}
        isOpen={isSchemaModalOpen}
        onClose={() => setIsSchemaModalOpen(false)}
        onReSeed={handleReSeed}
      />

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
      <KnowledgeBaseModal isOpen={isKnowledgeModalOpen} onClose={() => setIsKnowledgeModalOpen(false)} />

      {/* API Key Modal with Live Test Verification */}
      {isApiKeyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-white rounded-3xl p-6 relative shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <Key className="w-5 h-5 text-lime-500" />
              Configure & Verify LLM API Key
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter your Google Gemini or OpenAI API key. Click <strong>"Check API Key"</strong> to verify live connection.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-extrabold text-slate-700 block mb-1">
                  Select Provider:
                </label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 px-4 py-2 rounded-2xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-lime-400 mb-3"
                >
                  <option value="gemini">Google Gemini 1.5 Flash</option>
                  <option value="openai">OpenAI GPT-4o</option>
                  <option value="fallback">Deterministic Engine (No Key Needed)</option>
                </select>

                <label className="text-xs font-extrabold text-slate-700 block mb-1">
                  API Key Credential:
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    setKeyVerifyResult(null);
                  }}
                  placeholder="AIzaSy... / sk-..."
                  className="w-full bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-2xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-lime-400 font-mono"
                />
              </div>

              {/* Verification Result Box */}
              {keyVerifyResult && (
                <div
                  className={`p-3 rounded-2xl text-xs font-semibold flex items-center space-x-2 border ${
                    keyVerifyResult.valid
                      ? 'bg-lime-50 border-lime-300 text-lime-900'
                      : 'bg-rose-50 border-rose-300 text-rose-900'
                  }`}
                >
                  {keyVerifyResult.valid ? (
                    <CheckCircle2 className="w-4 h-4 text-lime-600 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  )}
                  <span>{keyVerifyResult.message}</span>
                </div>
              )}

              <div className="flex justify-between items-center pt-2 border-t border-slate-100">
                <button
                  onClick={handleVerifyApiKey}
                  disabled={isVerifyingKey}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all disabled:opacity-50"
                >
                  {isVerifyingKey ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-900" />
                      <span>Testing Key...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5 text-lime-600" />
                      <span>Check API Key</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => setIsApiKeyModalOpen(false)}
                  className="px-5 py-2 rounded-full bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-all shadow-sm"
                >
                  Save & Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
