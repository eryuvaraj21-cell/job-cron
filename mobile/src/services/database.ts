import * as SQLite from 'expo-sqlite';

let _db: SQLite.SQLiteDatabase | null = null;

async function db(): Promise<SQLite.SQLiteDatabase> {
  if (!_db) {
    _db = await SQLite.openDatabaseAsync('jobbot.db');
    await _db.execAsync(`
      PRAGMA journal_mode = WAL;
      CREATE TABLE IF NOT EXISTS jobs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id     TEXT    UNIQUE NOT NULL,
        title      TEXT    NOT NULL,
        company    TEXT,
        location   TEXT,
        url        TEXT    UNIQUE NOT NULL,
        description TEXT,
        skills     TEXT,
        match_score REAL   DEFAULT 0,
        status     TEXT    DEFAULT 'discovered',
        discovered_at TEXT,
        applied_at TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
      CREATE TABLE IF NOT EXISTS logs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        message   TEXT,
        level     TEXT DEFAULT 'info',
        timestamp TEXT
      );
    `);
  }
  return _db;
}

export interface LocalJob {
  id: number;
  job_id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  match_score: number;
  status: string;
  discovered_at: string;
  applied_at: string | null;
}

export interface LocalStats {
  total: number;
  applied: number;
  manual_needed: number;
  skipped: number;
  failed: number;
  today_total: number;
  today_applied: number;
}

export async function isNewJob(jobId: string): Promise<boolean> {
  const d = await db();
  const r = await d.getFirstAsync<{ c: number }>(
    'SELECT COUNT(*) AS c FROM jobs WHERE job_id = ?',
    [jobId],
  );
  return (r?.c ?? 0) === 0;
}

export async function saveJob(params: {
  jobId: string;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  skills: string[];
  matchScore: number;
  status: string;
}): Promise<void> {
  const d = await db();
  await d.runAsync(
    `INSERT OR IGNORE INTO jobs
     (job_id,title,company,location,url,description,skills,match_score,status,discovered_at)
     VALUES (?,?,?,?,?,?,?,?,?,?)`,
    [
      params.jobId,
      params.title,
      params.company,
      params.location,
      params.url,
      params.description,
      params.skills.join(','),
      params.matchScore,
      params.status,
      new Date().toISOString(),
    ],
  );
}

export async function updateJobStatus(jobId: string, status: string): Promise<void> {
  const d = await db();
  const appliedAt = status === 'applied' ? new Date().toISOString() : null;
  await d.runAsync(
    'UPDATE jobs SET status=?, applied_at=COALESCE(?,applied_at) WHERE job_id=?',
    [status, appliedAt, jobId],
  );
}

export async function getJobs(limit = 100, status = ''): Promise<LocalJob[]> {
  const d = await db();
  if (status) {
    return d.getAllAsync<LocalJob>(
      'SELECT * FROM jobs WHERE status=? ORDER BY discovered_at DESC LIMIT ?',
      [status, limit],
    );
  }
  return d.getAllAsync<LocalJob>(
    'SELECT * FROM jobs ORDER BY discovered_at DESC LIMIT ?',
    [limit],
  );
}

export async function getStats(): Promise<LocalStats> {
  const d = await db();
  const today = new Date().toISOString().slice(0, 10);
  const all = await d.getFirstAsync<{
    total: number; applied: number; manual_needed: number; skipped: number; failed: number;
  }>(`SELECT
       COUNT(*) total,
       SUM(CASE WHEN status='applied'       THEN 1 ELSE 0 END) applied,
       SUM(CASE WHEN status='manual_needed' THEN 1 ELSE 0 END) manual_needed,
       SUM(CASE WHEN status='skipped'       THEN 1 ELSE 0 END) skipped,
       SUM(CASE WHEN status='failed'        THEN 1 ELSE 0 END) failed
     FROM jobs`);
  const todayRow = await d.getFirstAsync<{ total: number; applied: number }>(
    `SELECT COUNT(*) total,
            SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) applied
     FROM jobs WHERE date(discovered_at)=?`,
    [today],
  );
  return {
    total:          all?.total          ?? 0,
    applied:        all?.applied        ?? 0,
    manual_needed:  all?.manual_needed  ?? 0,
    skipped:        all?.skipped        ?? 0,
    failed:         all?.failed         ?? 0,
    today_total:    todayRow?.total     ?? 0,
    today_applied:  todayRow?.applied   ?? 0,
  };
}

export async function addLog(message: string, level = 'info'): Promise<void> {
  const d = await db();
  await d.runAsync(
    'INSERT INTO logs(message,level,timestamp) VALUES(?,?,?)',
    [message, level, new Date().toISOString()],
  );
}

export async function getLogs(last = 150): Promise<Array<{ message: string; level: string; timestamp: string }>> {
  const d = await db();
  return d.getAllAsync(
    'SELECT message,level,timestamp FROM logs ORDER BY id DESC LIMIT ?',
    [last],
  );
}

export async function clearLogs(): Promise<void> {
  const d = await db();
  await d.runAsync('DELETE FROM logs');
}
