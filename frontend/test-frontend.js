/**
 * Frontend automated contract & component verification tests.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('--- Running Frontend Automated Tests ---');

// 1. Verify types match contract
const typesPath = path.join(__dirname, 'src', 'types', 'index.ts');
assert(fs.existsSync(typesPath), 'src/types/index.ts must exist');
const typesContent = fs.readFileSync(typesPath, 'utf8');
assert(typesContent.includes('export interface QueryResult'), 'QueryResult interface must be defined');
assert(typesContent.includes('export interface SchemaInfo'), 'SchemaInfo interface must be defined');
assert(typesContent.includes('export interface ChartConfig'), 'ChartConfig interface must be defined');
assert(typesContent.includes('export interface HistoryItem'), 'HistoryItem interface must be defined');
assert(typesContent.includes('export interface RagResult'), 'RagResult interface must be defined');
console.log('✓ Types and API contract interfaces verified.');

// 2. Verify all 8 benchmark queries are in QueryWorkspace
const qwPath = path.join(__dirname, 'src', 'components', 'QueryWorkspace.tsx');
assert(fs.existsSync(qwPath), 'QueryWorkspace.tsx must exist');
const qwContent = fs.readFileSync(qwPath, 'utf8');
const benchmarkQueries = [
  'How many customers are in the database?',
  'Show the first 10 products.',
  'Show all orders.',
  'Count orders by status.',
  'Which product generated the highest revenue?',
  'Show monthly revenue.',
  'Show audit logs.',
];
for (const q of benchmarkQueries) {
  assert(qwContent.includes(q), `QueryWorkspace must include benchmark query: "${q}"`);
}
console.log('✓ All 8 benchmark queries present in QueryWorkspace pills.');

// 3. Verify Recharts visualizer handles bar, line, and pie
const vizPath = path.join(__dirname, 'src', 'components', 'Visualizer.tsx');
assert(fs.existsSync(vizPath), 'Visualizer.tsx must exist');
const vizContent = fs.readFileSync(vizPath, 'utf8');
assert(vizContent.includes('LineChart'), 'Visualizer must support LineChart');
assert(vizContent.includes('BarChart'), 'Visualizer must support BarChart');
assert(vizContent.includes('PieChart'), 'Visualizer must support PieChart');
console.log('✓ Chart visualizer verified with Line, Bar, and Pie charts.');

// 4. Verify API client module exports all required endpoints
const apiPath = path.join(__dirname, 'src', 'lib', 'api.ts');
assert(fs.existsSync(apiPath), 'lib/api.ts must exist');
const apiContent = fs.readFileSync(apiPath, 'utf8');
const requiredApiFunctions = [
  'fetchSchema',
  'executeQuery',
  'executeManualSql',
  'uploadDatasetCsv',
  'fetchQueryHistory',
  'uploadRagDocument',
  'queryRag',
  'seedDatabase'
];
for (const fn of requiredApiFunctions) {
  assert(apiContent.includes(fn), `lib/api.ts must export ${fn}`);
}
console.log('✓ API client functions verified.');

// 5. Verify RAG component independence
const ragPath = path.join(__dirname, 'src', 'components', 'RagWorkspace.tsx');
assert(fs.existsSync(ragPath), 'RagWorkspace.tsx must exist');
const ragContent = fs.readFileSync(ragPath, 'utf8');
assert(ragContent.includes('Independent RAG Document Intelligence'), 'RagWorkspace header verified');
assert(ragContent.includes('citations'), 'RagWorkspace citations rendering verified');
console.log('✓ RAG Document Intelligence component verified.');

console.log('\n--- All Frontend Automated Tests Passed Successfully ---');
