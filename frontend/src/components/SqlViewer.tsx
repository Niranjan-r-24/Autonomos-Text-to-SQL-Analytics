'use client';

import React, { useState } from 'react';
import { Code2, Copy, Check, Play, Edit3 } from 'lucide-react';

interface SqlViewerProps {
  sql: string;
  onRunCustomSql?: (customSql: string) => void;
  isPipelineRunning?: boolean;
}

export const SqlViewer: React.FC<SqlViewerProps> = ({
  sql,
  onRunCustomSql,
  isPipelineRunning
}) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSql, setEditedSql] = useState(sql);

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

  return (
    <div className="w-full clay-card p-5 space-y-3 shadow-sm border border-slate-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-full bg-slate-900 text-lime-400 flex items-center justify-center">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-extrabold text-slate-900 flex items-center gap-2">
              Generated ANSI SQL Code
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold">
                ANSI Standard
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">Auto-formatted database query</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              setIsEditing(!isEditing);
              setEditedSql(sql);
            }}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>{isEditing ? 'Cancel' : 'Edit SQL'}</span>
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all shadow-sm"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-lime-400" />
                <span className="text-lime-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-400" />
                <span>Copy SQL</span>
              </>
            )}
          </button>

          {isEditing && (
            <button
              onClick={handleRunEdited}
              disabled={isPipelineRunning}
              className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-lime-400 hover:bg-lime-300 text-slate-900 text-xs font-extrabold transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Edited SQL</span>
            </button>
          )}
        </div>
      </div>

      {/* SQL Display Box */}
      <div className="p-4 rounded-2xl bg-slate-900 text-lime-300 font-mono text-xs overflow-x-auto leading-relaxed shadow-inner">
        {isEditing ? (
          <textarea
            value={editedSql}
            onChange={(e) => setEditedSql(e.target.value)}
            rows={4}
            className="w-full bg-transparent text-lime-300 p-2 font-mono text-xs focus:outline-none"
          />
        ) : (
          <pre>
            <code>{sql || '-- No SQL query generated yet.'}</code>
          </pre>
        )}
      </div>
    </div>
  );
};
