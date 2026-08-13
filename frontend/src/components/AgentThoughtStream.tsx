'use client';

import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronRight, CheckCircle2, Clock, Bot } from 'lucide-react';
import { AgentStep } from './Sidebar';

interface AgentThoughtStreamProps {
  agentSteps: AgentStep[];
  totalTimeSec?: number;
}

export const AgentThoughtStream: React.FC<AgentThoughtStreamProps> = ({
  agentSteps,
  totalTimeSec
}) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!agentSteps || agentSteps.length === 0) return null;

  return (
    <div className="w-full clay-card p-5 space-y-3 shadow-sm border border-slate-200">
      {/* Humanized Assistant Stream Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-full bg-slate-900 text-lime-400 flex items-center justify-center">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-extrabold text-slate-900 flex items-center gap-2">
              Orvion AI Reasoning Stream
              <span className="px-2 py-0.5 rounded-full bg-lime-400 text-slate-900 text-[10px] font-bold">
                Humanized Pipeline
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">Autonomous step-by-step logic execution</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {totalTimeSec !== undefined && (
            <span className="text-[11px] font-bold text-slate-700 bg-slate-100 px-3 py-1 rounded-full flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              <span>Execution Time: {totalTimeSec}s</span>
            </span>
          )}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-900"
          >
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Thought Stream List */}
      {isOpen && (
        <div className="pt-2 space-y-2.5">
          {agentSteps.map((step, idx) => (
            <div key={idx} className="p-3 rounded-2xl bg-slate-50 border border-slate-100 space-y-1">
              <div className="flex items-center justify-between text-slate-900 font-bold text-xs">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-lime-500" />
                  {step.agent_name}
                </span>
                {step.execution_time_sec !== undefined && (
                  <span className="text-[10px] text-slate-400 font-mono">
                    {step.execution_time_sec}s
                  </span>
                )}
              </div>

              {step.thought_logs && (
                <div className="pl-5 space-y-1 text-xs text-slate-600 font-medium">
                  {step.thought_logs.map((log, lIdx) => (
                    <div key={lIdx} className="flex items-start space-x-2">
                      <span className="text-slate-400">•</span>
                      <span>{log}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
