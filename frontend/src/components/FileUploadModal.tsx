'use client';

import React, { useState, useRef } from 'react';
import axios from 'axios';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle, X, Loader2, Table, ArrowRight
} from 'lucide-react';
import { API_BASE } from '@/config/api';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (tableName: string, schema: Record<string, any>) => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const supportedFormats = [
    { label: '.CSV', desc: 'Comma Separated' },
    { label: '.XLSX / .XLS', desc: 'Excel Sheets' },
    { label: '.JSON', desc: 'JSON Records' },
    { label: '.DB / .SQLITE', desc: 'SQLite DB File' },
    { label: '.SQL', desc: 'SQL Dump Script' },
    { label: '.TSV / .TXT', desc: 'Tab Separated' },
    { label: '.PARQUET', desc: 'Parquet File' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await axios.post(`${API_BASE}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (res.data && res.data.success) {
        setUploadResult(res.data);
        if (onUploadSuccess) {
          onUploadSuccess(res.data.table_name, res.data.schema);
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'File upload failed.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl bg-[#FFFFFF] rounded-2xl overflow-hidden shadow-2xl border border-[#E2E8F0] flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center shadow-2xs">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[#0F172A] flex items-center gap-2">
                Import Dataset
                <span className="px-2 py-0.5 rounded-md bg-[#ECFDF5] text-[#047857] text-[10px] font-bold border border-[#10B981]/30 uppercase">
                  10+ Formats
                </span>
              </h2>
              <p className="text-xs text-[#64748B]">
                Upload custom datasets to instantly query with Text-to-SQL AI
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-[#64748B] hover:text-[#0F172A] hover:bg-[#E2E8F0] flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {/* Supported Format Pills */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#047857] block mb-2">
              Supported Data Formats:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {supportedFormats.map((fmt) => (
                <span
                  key={fmt.label}
                  className="px-2.5 py-1 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] text-[11px] font-semibold text-[#0F172A]"
                >
                  {fmt.label}
                </span>
              ))}
            </div>
          </div>

          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`p-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center flex flex-col items-center justify-center space-y-3 ${
              isDragOver
                ? 'border-[#10B981] bg-[#ECFDF5]/50'
                : selectedFile
                ? 'border-[#10B981]/50 bg-[#F8FAFC]'
                : 'border-[#CBD5E1] bg-[#F8FAFC] hover:border-[#10B981]/60'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".csv,.xlsx,.xls,.json,.db,.sqlite,.sqlite3,.sql,.tsv,.txt,.parquet"
              className="hidden"
            />

            <div className="w-12 h-12 rounded-xl bg-[#FFFFFF] shadow-2xs border border-[#E2E8F0] flex items-center justify-center text-[#10B981]">
              <FileText className="w-6 h-6" />
            </div>

            {selectedFile ? (
              <div>
                <span className="text-xs font-bold text-[#0F172A] block truncate max-w-md">
                  {selectedFile.name}
                </span>
                <span className="text-[10px] text-[#64748B] font-mono">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Click or drag to replace
                </span>
              </div>
            ) : (
              <div>
                <p className="text-xs font-bold text-[#0F172A] mb-0.5">
                  Drag and drop your dataset here, or <span className="text-[#10B981] underline">browse</span>
                </p>
                <p className="text-[10px] text-[#64748B]">
                  Supports .csv, .xlsx, .json, .db, .sqlite, .sql, .tsv, .parquet
                </p>
              </div>
            )}
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Success Summary Card */}
          {uploadResult && (
            <div className="p-4 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#0F172A] space-y-2">
              <div className="flex items-center space-x-2 text-[#047857] text-xs font-bold">
                <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                <span>{uploadResult.message}</span>
              </div>

              {uploadResult.columns && (
                <div className="text-[11px] text-[#047857] font-medium pt-1 border-t border-[#10B981]/20">
                  Registered Table: <span className="font-mono font-bold text-[#0F172A]">{uploadResult.table_name}</span> ({uploadResult.row_count} rows)
                  <div className="flex flex-wrap gap-1 mt-1.5 font-mono text-[10px]">
                    {uploadResult.columns.map((c: string) => (
                      <span key={c} className="px-2 py-0.5 rounded bg-[#FFFFFF] text-[#0F172A] border border-[#10B981]/30">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2.5 pt-2 border-t border-[#E2E8F0]">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A] border border-[#E2E8F0] text-xs font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>

            {uploadResult ? (
              <button
                onClick={onClose}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white text-xs font-bold shadow-md shadow-[#10B981]/20 transition-all cursor-pointer"
              >
                <span>Query Ingested Dataset</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white disabled:bg-[#E2E8F0] disabled:text-[#94A3B8] text-xs font-bold shadow-md shadow-[#10B981]/20 transition-all cursor-pointer disabled:shadow-none"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                    <span>Importing Dataset...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>Upload & Register</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
