'use client';

import React, { useState } from 'react';
import {
  BarChart2, Database,
  CheckCircle2, Clock, AlertTriangle, Loader2, Sparkles, Code2, Wrench
} from 'lucide-react';

export interface AgentStep {
  agent_id: 'schema_linker' | 'sql_generator' | 'self_corrector' | 'visualizer' | 'rag_retriever';
  agent_name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  execution_time_sec?: number;
  output_summary?: string;
  thought_logs?: string[];
  data?: any;
}

interface SidebarProps {
  agentSteps: AgentStep[];
  isPipelineRunning: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  agentSteps,
  isPipelineRunning,
}) => {
  const [showDrawer, setShowDrawer] = useState(true);

  const getAgentIcon = (id: string) => {
    switch (id) {
      case 'schema_linker':
        return Database;
      case 'sql_generator':
        return Code2;
      case 'self_corrector':
        return Wrench;
      case 'visualizer':
        return BarChart2;
      case 'rag_retriever':
        return Sparkles;
      default:
        return Sparkles;
    }
  };

  const defaultAgents: AgentStep[] = [
    { agent_id: 'rag_retriever', agent_name: 'RAG Retrieval Agent', status: 'PENDING' },
    { agent_id: 'schema_linker', agent_name: 'Schema Linker Agent', status: 'PENDING' },
    { agent_id: 'sql_generator', agent_name: 'SQL Generator Agent', status: 'PENDING' },
    { agent_id: 'self_corrector', agent_name: 'Self-Correction Agent', status: 'PENDING' },
    { agent_id: 'visualizer', agent_name: 'Visualization Agent', status: 'PENDING' },
  ];

  const currentSteps = defaultAgents.map((def) => {
    const found = agentSteps.find((s) => s.agent_id === def.agent_id);
    return found || def;
  });

  return (
    <aside className="h-[calc(100vh-80px)] sticky top-[80px] shrink-0 pl-6 py-2 z-30">
      {/* Persistent agent status; navigation lives in the header. */}
      {showDrawer && (
        <div className="w-64 bg-white/90 backdrop-blur-md rounded-3xl border border-slate-200 p-4 shadow-clay-card flex flex-col justify-between overflow-y-auto">
          <div>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
              <span className="text-xs font-extrabold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-lime-500" />
                AI Agents Pipeline
              </span>
              {isPipelineRunning && (
                <span className="w-2 h-2 rounded-full bg-lime-400 animate-ping" />
              )}
            </div>

            {/* Agent Step Cards */}
            <div className="space-y-3">
              {currentSteps.map((step) => {
                const Icon = getAgentIcon(step.agent_id);
                const isCompleted = step.status === 'COMPLETED';
                const isRunning = step.status === 'RUNNING';
                const isFailed = step.status === 'FAILED';

                return (
                  <div
                    key={step.agent_id}
                    className={`p-3 rounded-2xl border transition-all ${
                      isCompleted
                        ? 'bg-slate-50/80 border-slate-200'
                        : isRunning
                        ? 'bg-lime-50 border-lime-300 ring-2 ring-lime-200'
                        : isFailed
                        ? 'bg-rose-50 border-rose-200'
                        : 'bg-white border-slate-100 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center space-x-2">
                        <div
                          className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs ${
                            isCompleted
                              ? 'bg-slate-900 text-white'
                              : isRunning
                              ? 'bg-lime-400 text-slate-900 font-bold'
                              : 'bg-slate-200 text-slate-600'
                          }`}
                        >
                          <Icon className="w-3 h-3" />
                        </div>
                        <span className="text-xs font-bold text-slate-900 truncate max-w-[110px]">
                          {step.agent_name.replace(' Agent', '')}
                        </span>
                      </div>

                      {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" />}
                      {isRunning && <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-900" />}
                      {isFailed && <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />}
                    </div>

                    {isCompleted && step.output_summary && (
                      <p className="text-[10px] text-slate-500 font-medium truncate pt-1">
                        {step.output_summary}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 text-[10px] text-slate-400 text-center font-medium">
            3x Auto-Healing Enabled
          </div>
        </div>
      )}
    </aside>
  );
};
