/**
 * Core bot cycle — runs entirely on-device.
 * Mirrors the Python bot's pipeline:
 *   1. Login with Naukri credentials (if configured)
 *   2. Fetch recommended jobs (authenticated) OR keyword search (public)
 *   3. Score against user skills
 *   4. Save to local SQLite
 * No Python server or PC required.
 */
import { searchNaukri, getRecommendedJobs, getStoredToken, clearToken } from './naukri';
import { isNewJob, saveJob, getStats, addLog } from './database';
import { scoreJob } from './matcher';
import { loadSettings } from './settings';
import { sendJobsFoundNotification } from './notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STATUS_KEY = 'bot_run_status';

export interface RunStatus {
  running:    boolean;
  lastRun:    string | null;
  lastResult: string;
}

export async function getRunStatus(): Promise<RunStatus> {
  try {
    const raw = await AsyncStorage.getItem(STATUS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* */ }
  return { running: false, lastRun: null, lastResult: 'never' };
}

async function setRunStatus(s: Partial<RunStatus>): Promise<void> {
  const current = await getRunStatus();
  await AsyncStorage.setItem(STATUS_KEY, JSON.stringify({ ...current, ...s }));
}

async function log(msg: string, level = 'info'): Promise<void> {
  const ts = new Date().toLocaleTimeString();
  await addLog(`[${ts}] ${msg}`, level);
}

export async function runBotCycle(): Promise<{ newJobs: number; matched: number }> {
  const status = await getRunStatus();
  if (status.running) return { newJobs: 0, matched: 0 };

  await setRunStatus({ running: true, lastRun: new Date().toISOString() });

  let newJobs = 0;
  let matched = 0;

  try {
    const settings = await loadSettings();
    await log(`Starting cycle — ${settings.keywords.length} keyword(s) in ${settings.location}`);

    const seen    = new Set<string>();
    let authToken: string | null = null;

    // ── Step 1: Load cached session (set via WebView login in Settings) ───────
    if (settings.naukriEmail) {
      const stored = await getStoredToken();
      if (stored) {
        authToken = stored;
        await log('Using cached Naukri session (from WebView login)');
      } else {
        await log('No cached Naukri session — go to Settings → Naukri Account → Login via browser', 'error');
      }
    }

    // ── Step 2: Fetch jobs ───────────────────────────────────────────────────
    const allJobs: import('./naukri').NaukriJob[] = [];

    if (authToken && settings.useRecommended) {
      // Recommended jobs (personalised feed — mirrors Python bot's get_recommended_jobs)
      await log('Fetching recommended jobs from Naukri…');
      try {
        const rec = await getRecommendedJobs(authToken, settings.maxPagesPerSearch);
        await log(`Recommended jobs: ${rec.length} fetched`);
        for (const j of rec) seen.has(j.jobId) || (seen.add(j.jobId), allJobs.push(j));
      } catch (err: any) {
        await log(`Recommended jobs error: ${err?.message ?? err}`, 'error');
        // Token may have expired — clear it so next run re-logs in
        await clearToken();
        authToken = null;
      }
    }

    // Always also search by keyword (authenticated search returns better results when logged in)
    for (const keyword of settings.keywords) {
      await log(`Searching: "${keyword}" in ${settings.location}`);
      try {
        const jobs = await searchNaukri(
          keyword, settings.location, settings.experienceYears,
          settings.maxPagesPerSearch, authToken ?? undefined,
        );
        await log(`Found ${jobs.length} jobs for "${keyword}"`);
        for (const j of jobs) seen.has(j.jobId) || (seen.add(j.jobId), allJobs.push(j));
      } catch (err: any) {
        await log(`Error searching "${keyword}": ${err?.message ?? err}`, 'error');
      }
    }

    await log(`Total unique jobs this cycle: ${allJobs.length}`);

    // ── Step 3: Score + save ─────────────────────────────────────────────────
    for (const job of allJobs) {
      const isNew = await isNewJob(job.jobId);
      if (!isNew) continue;

      newJobs++;
      const score  = scoreJob(job, settings.skills);
      const status = score >= settings.minMatchScore ? 'matched' : 'skipped';
      if (score >= settings.minMatchScore) matched++;

      await saveJob({
        jobId: job.jobId, title: job.title, company: job.company,
        location: job.location, url: job.url, description: job.description,
        skills: job.skills, matchScore: score, status,
      });

      if (score >= settings.minMatchScore) {
        await log(`Match (${score}%): ${job.title} @ ${job.company}`);
      }
    }

    const stats = await getStats();
    await log(`Cycle done — ${newJobs} new, ${matched} matched | total: ${stats.total} applied: ${stats.applied}`);

    if (newJobs > 0) await sendJobsFoundNotification(newJobs, matched);
    await setRunStatus({ running: false, lastResult: 'success' });
  } catch (err: any) {
    const msg = err?.message ?? String(err);
    await log(`Cycle error: ${msg}`, 'error');
    await setRunStatus({ running: false, lastResult: `error: ${msg}` });
  }

  return { newJobs, matched };
}
