import AsyncStorage from '@react-native-async-storage/async-storage';
import axios, { AxiosInstance } from 'axios';

const STORAGE_KEY = 'api_base_url';
export const DEFAULT_BASE_URL = 'http://192.168.1.100:8080';

export async function getBaseUrl(): Promise<string> {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    return stored?.trim() || DEFAULT_BASE_URL;
  } catch {
    return DEFAULT_BASE_URL;
  }
}

export async function saveBaseUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, url.trim());
}

async function getClient(): Promise<AxiosInstance> {
  const base = await getBaseUrl();
  return axios.create({ baseURL: base, timeout: 10_000 });
}

// ── Typed response shapes ─────────────────────────────────────────────────────

export interface BotStatus {
  running: boolean;
  last_run: string | null;
  last_run_result: string;
}

export interface StatsPayload {
  today: Record<string, number>;
  all_time: {
    total: number;
    applied: number;
    manual_needed: number;
    skipped: number;
    failed: number;
  };
  date: string;
}

export interface Job {
  id: number;
  platform: string;
  title: string;
  company: string;
  location: string;
  url: string;
  match_score: number;
  status: string;
  discovered_at: string;
  applied_at: string | null;
}

export interface LogEntry {
  ts: string;
  msg: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function fetchStatus(): Promise<BotStatus> {
  const c = await getClient();
  return (await c.get<BotStatus>('/api/status')).data;
}

export async function triggerRun(): Promise<{ ok: boolean; message: string }> {
  const c = await getClient();
  return (await c.post('/api/run')).data;
}

export async function fetchStats(): Promise<StatsPayload> {
  const c = await getClient();
  return (await c.get<StatsPayload>('/api/stats')).data;
}

export async function fetchJobs(limit = 100, status = ''): Promise<Job[]> {
  const c = await getClient();
  const params: Record<string, string | number> = { limit };
  if (status) params.status = status;
  return (await c.get<Job[]>('/api/jobs', { params })).data;
}

export async function fetchLogs(last = 150): Promise<LogEntry[]> {
  const c = await getClient();
  return (await c.get<LogEntry[]>('/api/logs', { params: { last } })).data;
}

export async function testConnection(): Promise<boolean> {
  try {
    const c = await getClient();
    await c.get('/api/status', { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}
