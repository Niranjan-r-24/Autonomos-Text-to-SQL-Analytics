'use client';

import React, { useState, useEffect } from 'react';
import { Code2, Copy, Check, Play, Edit3, RotateCcw, ShieldCheck } from 'lucide-react';

interface SqlViewerProps {
  sql: string;
  onRunCustomSql?: (customSql: string) => void;
  isExecuting?: boolean;
}

export const SqlViewer: React.FC<SqlViewerProps> = ({
  sql,
  onRunCustomSql,
  isExecuting = false,
}) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSql, setEditedSql] = useState(sql);

  useEffect(() => {
    setEditedSql(sql);
  }, [sql]);

  const handleCopy = () => {
    navigator.clipboard.writeText(isEditing ? editedSql : sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRunEdited = () => {
    if (onRunCustomSql && editedSql.trim()) {
      onRunCustomSql(editedSql.trim());
    }
  };

  const handleReset = () => {
    setEditedSql(sql);
  };

  return (
    <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981]/40 rounded-2xl p-5 space-y-3 shadow-2xs transition-all">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center font-bold">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-[#0F172A] flex items-center gap-2">
              Generated SQL Statement
              <span className="px-2 py-0.5 rounded-md bg-[#F8FAFC] text-[#64748B] text-[10px] font-mono border border-[#E2E8F0]">
                ANSI SQLite
              </span>
            </h3>
            <p className="text-[11px] text-[#64748B]">Read-only SELECT query verified by AST Guard</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              setIsEditing(!isEditing);
              if (isEditing) setEditedSql(sql);
            }}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              isEditing
                ? 'bg-amber-50 text-amber-900 border border-amber-300'
                : 'bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] border border-[#E2E8F0]'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5 text-[#10B981]" />
            <span>{isEditing ? 'Cancel' : 'Edit SQL'}</span>
          </button>

          {isEditing && (
            <button
              onClick={handleReset}
              title="Reset to generated SQL"
              className="p-1 rounded-lg bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A] border border-[#E2E8F0] transition-all cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] border border-[#E2E8F0] text-xs font-semibold transition-all cursor-pointer shadow-2xs"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
                <span className="text-[#047857]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-[#64748B]" />
                <span>Copy SQL</span>
              </>
            )}
          </button>

          {isEditing && (
            <button
              onClick={handleRunEdited}
              disabled={isExecuting || !editedSql.trim()}
              className="flex items-center space-x-1.5 px-4 py-1 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white text-xs font-bold transition-all shadow-md shadow-[#10B981]/20 disabled:opacity-50 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isExecuting ? 'Running...' : 'Run Query'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Code Editor / Viewer */}
      <div className="p-3.5 rounded-xl bg-[#F8FAFC] text-[#0F172A] font-mono text-xs overflow-x-auto leading-relaxed border border-[#E2E8F0] shadow-2xs">
        {isEditing ? (
          <textarea
            value={editedSql}
            onChange={(e) => setEditedSql(e.target.value)}
            rows={4}
            placeholder="Enter SQL SELECT query..."
            className="w-full bg-[#FFFFFF] text-[#0F172A] font-mono text-xs p-2 rounded-lg border border-[#CBD5E1] focus:outline-none focus:border-[#10B981] resize-y"
          />
        ) : (
          <pre className="whitespace-pre-wrap break-words">
            <code>{sql || '-- No SQL query generated yet.'}</code>
          </pre>
        )}
      </div>
    </div>
  );
};
