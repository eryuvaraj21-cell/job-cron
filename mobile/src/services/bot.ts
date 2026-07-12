/**
 * Core bot cycle — runs entirely on-device.
 * Fetches jobs via HTTP, scores them, saves to local SQLite.
 * No Python server or PC required.
 */
import { searchNaukri } from './naukri';
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

    const seen = new Set<string>();

    for (const keyword of settings.keywords) {
      await log(`Searching: "${keyword}" in ${settings.location}`);
      try {
        const jobs = await searchNaukri(
          keyword,
          settings.location,
          settings.experienceYears,
          settings.maxPagesPerSearch,
        );
        await log(`Found ${jobs.length} jobs for "${keyword}"`);

        for (const job of jobs) {
          if (seen.has(job.jobId)) continue;
          seen.add(job.jobId);

          const isNew = await isNewJob(job.jobId);
          if (!isNew) continue;

          newJobs++;
          const score = scoreJob(job, settings.skills);
          const status =
            score >= settings.minMatchScore ? 'matched' : 'skipped';

          if (score >= settings.minMatchScore) matched++;

          await saveJob({
            jobId:       job.jobId,
            title:       job.title,
            company:     job.company,
            location:    job.location,
            url:         job.url,
            description: job.description,
            skills:      job.skills,
            matchScore:  score,
            status,
          });

          if (score >= settings.minMatchScore) {
            await log(`Match (${score}%): ${job.title} @ ${job.company}`);
          }
        }
      } catch (err: any) {
        await log(`Error fetching "${keyword}": ${err?.message ?? err}`, 'error');
      }
    }

    const stats = await getStats();
    await log(
      `Cycle done — ${newJobs} new, ${matched} matched | total: ${stats.total} applied: ${stats.applied}`,
    );

    if (newJobs > 0) {
      await sendJobsFoundNotification(newJobs, matched);
    }

    await setRunStatus({ running: false, lastResult: 'success' });
  } catch (err: any) {
    const msg = err?.message ?? String(err);
    await log(`Cycle error: ${msg}`, 'error');
    await setRunStatus({ running: false, lastResult: `error: ${msg}` });
  }

  return { newJobs, matched };
}
