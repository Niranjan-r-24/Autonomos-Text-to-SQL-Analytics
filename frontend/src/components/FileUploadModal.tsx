'use client';

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle, X, Loader2, Table, ArrowRight, BookOpen, Trash2, HelpCircle
} from 'lucide-react';
import { API_BASE } from '@/config/api';

export interface DocumentMeta {
  filename: string;
  chunks: number;
  file_type?: string;
  size_bytes?: number;
  indexed_at?: string;
  status?: string;
}

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (tableName: string, schema: Record<string, any>) => void;
  onQueryDocument?: (docName: string) => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  onQueryDocument,
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'documents'>('upload');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusText, setUploadStatusText] = useState('Uploading & Processing...');
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [availableDocs, setAvailableDocs] = useState<DocumentMeta[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch document availability and reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedFiles([]);
      setUploadResult(null);
      setErrorMessage(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      fetchDocuments();
    }
  }, [isOpen]);

  const fetchDocuments = async () => {
    setIsLoadingDocs(true);
    try {
      const res = await axios.get(`${API_BASE}/api/rag/documents`);
      if (res.data && res.data.documents) {
        setAvailableDocs(res.data.documents);
      }
    } catch (err) {
      console.error('Failed to load documents list:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const handleDeleteDocument = async (filename: string) => {
    setDeletingDoc(filename);
    try {
      await axios.delete(`${API_BASE}/api/rag/documents/${encodeURIComponent(filename)}`);
      await fetchDocuments();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to delete document.';
      setErrorMessage(msg);
    } finally {
      setDeletingDoc(null);
    }
  };

  if (!isOpen) return null;

  const datasetFormats = [
    { label: '.CSV', desc: 'Tabular' },
    { label: '.XLSX', desc: 'Excel' },
    { label: '.JSON', desc: 'Records' },
    { label: '.SQL / .DB', desc: 'Database' },
    { label: '.PARQUET', desc: 'Columnar' },
  ];

  const documentFormats = [
    { label: '.PDF', desc: 'Acrobat PDF' },
    { label: '.DOCX', desc: 'Word Document' },
    { label: '.TXT / .MD', desc: 'Text & Markdown' },
  ];

  const getFileCategory = (name: string): 'document' | 'dataset' => {
    const ext = name.slice(name.lastIndexOf('.')).toLowerCase();
    if (['.pdf', '.docx', '.doc', '.txt', '.md'].includes(ext)) {
      return 'document';
    }
    return 'dataset';
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadResult(null);

    const importedTables: string[] = [];
    let latestSchema: Record<string, any> = {};
    let lastUploadData: any = null;

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const isDoc = getFileCategory(file.name) === 'document';
        setUploadStatusText(
          selectedFiles.length > 1
            ? `[${i + 1}/${selectedFiles.length}] Processing ${file.name}...`
            : isDoc
            ? 'Extracting text, chunking & indexing into RAG vector store...'
            : 'Importing dataset & building database schema...'
        );

        const formData = new FormData();
        formData.append('file', file);

        const res = await axios.post(`${API_BASE}/api/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        if (res.data && res.data.success) {
          lastUploadData = res.data;
          if (res.data.table_name && res.data.table_name !== 'knowledge_base') {
            importedTables.push(res.data.table_name);
          }
          if (res.data.schema) {
            latestSchema = res.data.schema;
          }
        } else {
          throw new Error(res.data?.message || `Failed to process ${file.name}`);
        }
      }

      await fetchDocuments();
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      const summaryResult = {
        ...lastUploadData,
        message:
          importedTables.length > 1
            ? `Successfully imported ${importedTables.length} datasets: ${importedTables.join(', ')}.`
            : lastUploadData?.message || 'File uploaded successfully.',
        imported_tables: importedTables,
        schema: latestSchema,
      };
      setUploadResult(summaryResult);

      const primaryTable = importedTables[0] || lastUploadData?.table_name || 'knowledge_base';
      if (onUploadSuccess) {
        onUploadSuccess(primaryTable, latestSchema);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'File upload failed.';
      setErrorMessage(msg);
      setUploadResult(null);
    } finally {
      setIsUploading(false);
    }
  };

  const isDocumentResult = uploadResult?.type === 'document' || Boolean(uploadResult?.rag_info);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-[#FFFFFF] rounded-2xl overflow-hidden shadow-2xl border border-[#E2E8F0] flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center shadow-2xs">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[#0F172A] flex items-center gap-2">
                Dataset & Document Hub
                <span className="px-2 py-0.5 rounded-md bg-[#ECFDF5] text-[#047857] text-[10px] font-bold border border-[#10B981]/30 uppercase">
                  SQL & RAG
                </span>
              </h2>
              <p className="text-xs text-[#64748B]">
                Upload CSV/Excel tables or PDF/DOCX/TXT knowledge documents for AI analytics
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

        {/* Navigation Tabs */}
        <div className="px-6 pt-3 border-b border-[#E2E8F0] bg-[#FFFFFF] flex items-center space-x-4">
          <button
            onClick={() => setActiveTab('upload')}
            className={`pb-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer ${
              activeTab === 'upload'
                ? 'border-[#10B981] text-[#047857]'
                : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            Upload New File
          </button>

          <button
            onClick={() => setActiveTab('documents')}
            className={`pb-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'documents'
                ? 'border-[#10B981] text-[#047857]'
                : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Document Availability</span>
            <span className="px-1.5 py-0.2 rounded-full bg-[#ECFDF5] text-[#047857] text-[10px] font-mono border border-[#10B981]/30">
              {availableDocs.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Upload New File */}
        {activeTab === 'upload' && (
          <div className="p-6 space-y-4 overflow-y-auto flex-1">
            {/* Format Categories */}
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#047857]">
                  Supported Knowledge Documents (RAG):
                </span>
                <div className="flex flex-wrap gap-1">
                  {documentFormats.map((fmt) => (
                    <span
                      key={fmt.label}
                      className="px-2 py-0.5 rounded-md bg-[#ECFDF5] border border-[#10B981]/30 text-[10px] font-bold text-[#047857]"
                    >
                      {fmt.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">
                  Supported Structured Datasets (SQL):
                </span>
                <div className="flex flex-wrap gap-1">
                  {datasetFormats.map((fmt) => (
                    <span
                      key={fmt.label}
                      className="px-2 py-0.5 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-[10px] font-semibold text-[#475569]"
                    >
                      {fmt.label}
                    </span>
                  ))}
                </div>
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
              className={`p-7 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center flex flex-col items-center justify-center space-y-2.5 ${
                isDragOver
                  ? 'border-[#10B981] bg-[#ECFDF5]/50'
                  : selectedFiles.length > 0
                  ? 'border-[#10B981]/50 bg-[#F8FAFC]'
                  : 'border-[#CBD5E1] bg-[#F8FAFC] hover:border-[#10B981]/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileChange}
                accept=".csv,.xlsx,.xls,.json,.db,.sqlite,.sqlite3,.sql,.tsv,.txt,.parquet,.pdf,.docx,.doc,.md"
                className="hidden"
              />

              <div className="w-11 h-11 rounded-xl bg-[#FFFFFF] shadow-2xs border border-[#E2E8F0] flex items-center justify-center text-[#10B981]">
                <FileText className="w-5 h-5" />
              </div>

              {selectedFiles.length > 0 ? (
                <div className="space-y-1">
                  <span className="text-xs font-bold text-[#0F172A] block truncate max-w-md">
                    {selectedFiles.length === 1
                      ? selectedFiles[0].name
                      : `${selectedFiles.length} files selected: ${selectedFiles.map((f) => f.name).join(', ')}`}
                  </span>
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-[10px] text-[#64748B] font-mono">
                      {(selectedFiles.reduce((acc, f) => acc + f.size, 0) / 1024).toFixed(1)} KB total
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.2 rounded-full border ${
                        selectedFiles.some((f) => getFileCategory(f.name) === 'document')
                          ? 'bg-[#ECFDF5] text-[#047857] border-[#10B981]/30'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {selectedFiles.length === 1
                        ? (getFileCategory(selectedFiles[0].name) === 'document' ? 'Knowledge Document (RAG)' : 'Structured Dataset (SQL)')
                        : `${selectedFiles.length} Datasets & Files`}
                    </span>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-[#0F172A] mb-0.5">
                    Drag and drop your file here, or <span className="text-[#10B981] underline">browse</span>
                  </p>
                  <p className="text-[10px] text-[#64748B]">
                    PDF, DOCX, TXT, MD, CSV, Excel, JSON, SQLite
                  </p>
                </div>
              )}
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div
                className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center space-x-2"
                data-testid="upload-error-banner"
              >
                <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                <div className="space-y-0.5">
                  <span className="font-bold block">Upload Failed</span>
                  <span className="text-rose-700">{errorMessage}</span>
                </div>
              </div>
            )}

            {/* Success Summary Card */}
            {uploadResult && (
              <div
                className="p-4 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#0F172A] space-y-2.5 shadow-2xs"
                data-testid="upload-success-card"
              >
                <div className="flex items-center space-x-2 text-[#047857] text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  <span>{uploadResult.message}</span>
                </div>

                {isDocumentResult ? (
                  <div className="text-[11px] text-[#047857] font-medium pt-1.5 border-t border-[#10B981]/20 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-[#10B981]" />
                        Indexed Knowledge Base Document
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold border border-emerald-300">
                        Ready for Q&A
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-2 text-[10px] font-mono text-[#334155]">
                      <span className="px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#10B981]/30">
                        Chunks: {uploadResult.rag_info?.chunks_created || '1'}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#10B981]/30">
                        Total Library: {uploadResult.rag_info?.total_knowledge_chunks || availableDocs.length} chunks
                      </span>
                      <span className="px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#10B981]/30">
                        Storage: Persistent Chroma Store
                      </span>
                    </div>
                  </div>
                ) : uploadResult.columns ? (
                  <div className="text-[11px] text-[#047857] font-medium pt-1.5 border-t border-[#10B981]/20">
                    Registered Table: <span className="font-mono font-bold text-[#0F172A]">{uploadResult.table_name}</span> ({uploadResult.row_count} rows)
                    <div className="flex flex-wrap gap-1 mt-1.5 font-mono text-[10px]">
                      {uploadResult.columns.map((c: string) => (
                        <span key={c} className="px-2 py-0.5 rounded bg-[#FFFFFF] text-[#0F172A] border border-[#10B981]/30">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
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
                  onClick={() => {
                    // The selection is intentionally cleared after upload, so
                    // use the server-confirmed filename from the upload result.
                    if (isDocumentResult && onQueryDocument && uploadResult?.filename) {
                      onQueryDocument(uploadResult.filename);
                    }
                    onClose();
                  }}
                  className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white text-xs font-bold shadow-md shadow-[#10B981]/20 transition-all cursor-pointer"
                >
                  <span>{isDocumentResult ? 'Ask Questions About Document' : 'Dataset Ready'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleUpload}
                  disabled={selectedFiles.length === 0 || isUploading}
                  className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white disabled:bg-[#E2E8F0] disabled:text-[#94A3B8] text-xs font-bold shadow-md shadow-[#10B981]/20 transition-all cursor-pointer disabled:shadow-none"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                      <span>{uploadStatusText}</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      <span>Upload & Index</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Document Availability */}
        {activeTab === 'documents' && (
          <div className="p-6 space-y-4 overflow-y-auto flex-1">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#047857]">
                  Indexed RAG Knowledge Base Documents
                </h3>
                <p className="text-[11px] text-[#64748B]">
                  Documents stored, chunked, and available for natural language Q&A with source citations
                </p>
              </div>

              <button
                onClick={fetchDocuments}
                className="text-[11px] font-semibold text-[#10B981] hover:underline cursor-pointer"
              >
                Refresh List
              </button>
            </div>

            {isLoadingDocs ? (
              <div className="p-8 text-center text-[#64748B] flex items-center justify-center space-x-2 text-xs">
                <Loader2 className="w-4 h-4 animate-spin text-[#10B981]" />
                <span>Checking document availability...</span>
              </div>
            ) : availableDocs.length === 0 ? (
              <div className="p-8 text-center bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
                <BookOpen className="w-8 h-8 text-[#94A3B8] mx-auto" />
                <p className="text-xs font-bold text-[#0F172A]">No Documents Indexed Yet</p>
                <p className="text-[11px] text-[#64748B]">
                  Upload PDF, DOCX, or TXT documents to enable retrieval-augmented generation.
                </p>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="mt-2 px-3 py-1.5 rounded-lg bg-[#10B981] text-white text-xs font-bold cursor-pointer"
                >
                  Upload First Document
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {availableDocs.map((doc) => {
                  const ext = doc.file_type || doc.filename.slice(doc.filename.lastIndexOf('.')).toLowerCase();
                  return (
                    <div
                      key={doc.filename}
                      className="p-3 bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981]/50 rounded-xl flex items-center justify-between gap-3 shadow-2xs transition-all"
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center shrink-0">
                          <BookOpen className="w-4 h-4" />
                        </div>

                        <div className="min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold text-[#0F172A] truncate">
                              {doc.filename}
                            </span>
                            <span className="px-1.5 py-0.2 rounded bg-[#F1F5F9] text-[#475569] text-[9px] font-mono font-bold uppercase">
                              {ext.replace('.', '')}
                            </span>
                          </div>

                          <div className="flex items-center space-x-3 text-[10px] text-[#64748B] font-mono pt-0.5">
                            <span>{doc.chunks} chunks</span>
                            <span>•</span>
                            <span>{doc.size_bytes ? `${(doc.size_bytes / 1024).toFixed(1)} KB` : 'Indexed'}</span>
                            <span>•</span>
                            <span className="text-emerald-700 font-semibold flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              Ready for Q&A
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-1.5 shrink-0">
                        {onQueryDocument && (
                          <button
                            onClick={() => {
                              onQueryDocument(doc.filename);
                              onClose();
                            }}
                            className="px-2.5 py-1 rounded-lg bg-[#ECFDF5] hover:bg-[#D1FAE5] text-[#047857] text-[11px] font-bold border border-[#10B981]/30 transition-colors cursor-pointer"
                            title="Ask questions about this document"
                          >
                            Query
                          </button>
                        )}

                        <button
                          onClick={() => handleDeleteDocument(doc.filename)}
                          disabled={deletingDoc === doc.filename}
                          className="p-1.5 rounded-lg text-[#94A3B8] hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer disabled:opacity-50"
                          title="Delete from knowledge base"
                        >
                          {deletingDoc === doc.filename ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="pt-2 border-t border-[#E2E8F0] flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#64748B] text-xs font-semibold border border-[#E2E8F0] cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
