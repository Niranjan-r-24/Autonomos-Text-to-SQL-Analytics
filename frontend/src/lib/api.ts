import axios from 'axios';
import { SchemaInfo, QueryResult, HistoryItem, RagResult } from '@/types';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export async function fetchSchema(refresh: boolean = false): Promise<SchemaInfo> {
  const res = await client.get<SchemaInfo>(`/api/schema?refresh=${refresh}`);
  return res.data;
}

export async function executeQuery(
  question: string,
  provider?: string,
  apiKey?: string
): Promise<QueryResult> {
  const res = await client.post<QueryResult>('/api/query', {
    question,
    provider: provider || undefined,
    api_key: apiKey || undefined,
  });
  return res.data;
}

export async function executeManualSql(sql: string): Promise<QueryResult> {
  const res = await client.post<QueryResult>('/api/execute-sql', { sql });
  return res.data;
}

export async function uploadDatasetCsv(file: File, tableName?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (tableName) {
    formData.append('table_name', tableName);
  }
  const res = await client.post('/api/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function fetchQueryHistory(limit: number = 50): Promise<HistoryItem[]> {
  const res = await client.get<{ status: string; history: HistoryItem[] }>(`/api/history?limit=${limit}`);
  return res.data.history;
}

export async function clearQueryHistory(): Promise<void> {
  await client.delete('/api/history');
}

export async function uploadRagDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post('/api/rag/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function queryRag(query: string): Promise<RagResult> {
  const res = await client.post<RagResult>('/api/rag/query', { query });
  return res.data;
}

export async function seedDatabase(force: boolean = true) {
  const res = await client.post(`/api/db/seed?force=${force}`);
  return res.data;
}
