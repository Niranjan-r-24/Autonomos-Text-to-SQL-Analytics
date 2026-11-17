import axios from 'axios';
import { SchemaInfo, QueryResult, HistoryItem, RagResult } from '@/types';

const getApiBase = () => {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  return '';
};

const client = axios.create({
  baseURL: getApiBase(),
  timeout: 30000,
});

export async function fetchSchema(refresh: boolean = false): Promise<SchemaInfo> {
  try {
    const res = await client.get<SchemaInfo>(`/api/schema?refresh=${refresh}`);
    if (res.data && typeof res.data === 'object' && res.data.tables) {
      return res.data;
    }
    return {
      status: 'ok',
      tables: {},
      table_names: [],
      relationships: [],
    };
  } catch (err) {
    console.warn('API fetchSchema failed, using fallback empty schema:', err);
    return {
      status: 'offline',
      tables: {},
      table_names: [],
      relationships: [],
    };
  }
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
  try {
    const res = await client.get<{ status: string; history: HistoryItem[] }>(`/api/history?limit=${limit}`);
    return Array.isArray(res.data?.history) ? res.data.history : [];
  } catch (err) {
    console.warn('Failed to fetch query history:', err);
    return [];
  }
}

export async function clearQueryHistory(): Promise<void> {
  try {
    await client.delete('/api/history');
  } catch (err) {
    console.warn('Failed to clear history:', err);
  }
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
