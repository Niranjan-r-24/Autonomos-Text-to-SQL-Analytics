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
import { Sparkles, AlertCircle, ArrowUpRight, Bot, ShieldCheck, Zap } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [query, setQuery] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [isSchemaModalOpen, setIsSchemaModalOpen] = useState(false);

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
      {/* Top Header Navigation matching Orvion bar */}
      <Header
        apiKey={apiKey}
        setApiKey={setApiKey}
        provider={provider}
        setProvider={setProvider}
        onOpenSchema={() => setIsSchemaModalOpen(true)}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Floating Icon Pillar & Agent Workflow Drawer */}
        <Sidebar
          agentSteps={agentSteps}
          isPipelineRunning={isPipelineRunning}
          onOpenSchema={() => setIsSchemaModalOpen(true)}
        />

        {/* Main Canvas Center Dashboard Content */}
        <main className="flex-1 p-8 overflow-y-auto space-y-7 max-w-7xl mx-auto">
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

          {/* Banner Hero Widget matching the 3D organic lime card in reference image */}
          {!pipelineResult && !isPipelineRunning && (
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* 3D Organic Lime Banner Card */}
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
        </main>
      </div>

      {/* Enterprise Schema Inspector Modal */}
      <SchemaViewerModal
        schema={schemaData}
        isOpen={isSchemaModalOpen}
        onClose={() => setIsSchemaModalOpen(false)}
        onReSeed={handleReSeed}
      />
    </div>
  );
}
