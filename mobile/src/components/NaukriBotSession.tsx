/**
 * NaukriBotSession — full WebView automation that mirrors the Python Selenium bot.
 *
 * Flow (identical to Python bot with BROWSER_HEADLESS=False):
 *   1. Navigate to nlogin/login  →  auto-fill credentials  →  submit
 *   2. Detect login success (URL leaves /nlogin/)
 *   3. Navigate to recommended jobs page
 *   4. Inject JS to scrape job cards
 *   5. Score each job against user skills
 *   6. For each matched job: navigate → inject Easy Apply script → confirm
 *   7. Show live log + results  →  push notification when done
 */
import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Modal,
  ScrollView, ActivityIndicator,
} from 'react-native';
import { WebView, WebViewNavigation } from 'react-native-webview';
import { C } from '../theme';
import {
  loginScript, SCRAPE_JOBS_SCRIPT, EASY_APPLY_SCRIPT,
  NAUKRI, ScrapedJob, BotMsg,
} from '../services/botScript';
import { loadSettings }              from '../services/settings';
import { scoreJob }                  from '../services/matcher';
import { isNewJob, saveJob, updateJobStatus, addLog } from '../services/database';
import { sendJobsFoundNotification } from '../services/notifications';

// ── Types ─────────────────────────────────────────────────────────────────────

type Step =
  | 'login'        // loading login page
  | 'filling'      // injecting credentials
  | 'logged_in'    // login success, navigating to recommended
  | 'get_jobs'     // loading recommended page
  | 'scraping'     // injecting scrape script
  | 'applying'     // navigating to job + injecting apply script
  | 'done'
  | 'error';

interface LogLine {
  ts:    string;
  msg:   string;
  level: 'info' | 'ok' | 'warn' | 'error';
}

export interface BotResult {
  applied:  number;
  skipped:  number;
  total:    number;
}

interface Props {
  onClose: (result: BotResult) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function NaukriBotSession({ onClose }: Props) {
  const wvRef         = useRef<WebView>(null);
  const scrollRef     = useRef<ScrollView>(null);
  const stepRef       = useRef<Step>('login');
  const jobQueueRef   = useRef<ScrapedJob[]>([]);
  const jobIdxRef     = useRef(0);
  const resultRef     = useRef<BotResult>({ applied: 0, skipped: 0, total: 0 });
  const settingsRef   = useRef<any>(null);
  const filledRef     = useRef(false);

  const [step,     setStep]     = useState<Step>('login');
  const [logs,     setLogs]     = useState<LogLine[]>([]);
  const [jobCount, setJobCount] = useState(0);
  const [jobIdx,   setJobIdx]   = useState(0);
  const [result,   setResult]   = useState<BotResult>({ applied: 0, skipped: 0, total: 0 });

  // ── Logging ─────────────────────────────────────────────────────────────────

  const log = useCallback((msg: string, level: LogLine['level'] = 'info') => {
    const entry: LogLine = { ts: new Date().toLocaleTimeString(), msg, level };
    setLogs(prev => {
      const next = [...prev, entry];
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
      return next;
    });
    addLog(msg, level === 'error' ? 'error' : 'info');
  }, []);

  const setStepBoth = useCallback((s: Step) => {
    stepRef.current = s;
    setStep(s);
  }, []);

  // ── Load settings on mount ───────────────────────────────────────────────────

  useEffect(() => {
    loadSettings().then(s => {
      settingsRef.current = s;
      if (!s.naukriEmail || !s.naukriPassword) {
        log('No Naukri credentials configured — go to Settings', 'error');
        setStepBoth('error');
      } else {
        log(`Starting bot for ${s.naukriEmail}`);
        log('Navigating to login page…');
      }
    });
  }, [log, setStepBoth]);

  // ── Process next job in queue ────────────────────────────────────────────────

  const processNextJob = useCallback(async () => {
    const queue = jobQueueRef.current;
    const idx   = jobIdxRef.current;
    const s     = settingsRef.current;

    if (idx >= queue.length) {
      const r = resultRef.current;
      log(`All done — Applied: ${r.applied}  Skipped: ${r.skipped}  Total: ${r.total}`, 'ok');
      setStepBoth('done');
      await sendJobsFoundNotification(r.applied, r.applied);
      return;
    }

    const job = queue[idx];
    setJobIdx(idx);

    // Already processed?
    const isNew = await isNewJob(job.jobId || job.url);
    if (!isNew) {
      log(`[${idx + 1}/${queue.length}] Already seen: ${job.title}`);
      jobIdxRef.current++;
      setTimeout(processNextJob, 100);
      return;
    }

    // Score
    const userSkills = s?.skills ?? [];
    const score = scoreJob(
      { skills: job.skills.split(',').map((sk: string) => sk.trim().toLowerCase()), title: job.title, description: '' } as any,
      userSkills,
    );
    const minScore = s?.minMatchScore ?? 30;

    log(`[${idx + 1}/${queue.length}] ${job.title} @ ${job.company}  (score ${score}%)`);

    if (score < minScore) {
      log(`  → Skipped (${score}% < ${minScore}%)`);
      await saveJob({ jobId: job.jobId || job.url, title: job.title, company: job.company, location: job.location, url: job.url, description: '', skills: job.skills.split(',').map((sk: string) => sk.trim()), matchScore: score, status: 'skipped' });
      resultRef.current.skipped++;
      resultRef.current.total++;
      setResult({ ...resultRef.current });
      jobIdxRef.current++;
      setTimeout(processNextJob, 200);
      return;
    }

    // Navigate to job + apply
    log(`  → Match! Navigating to apply…`, 'ok');
    await saveJob({ jobId: job.jobId || job.url, title: job.title, company: job.company, location: job.location, url: job.url, description: '', skills: job.skills.split(',').map((sk: string) => sk.trim()), matchScore: score, status: 'matched' });
    setStepBoth('applying');
    wvRef.current?.injectJavaScript(`window.location.href = ${JSON.stringify(job.url)}; true;`);
  }, [log, setStepBoth]);

  // ── WebView callbacks ────────────────────────────────────────────────────────

  const handleLoadEnd = useCallback(() => {
    const s = settingsRef.current;
    const step = stepRef.current;

    if (step === 'login' && !filledRef.current && s?.naukriEmail) {
      filledRef.current = true;
      setStepBoth('filling');
      log('Page loaded — filling credentials…');
      setTimeout(() => {
        wvRef.current?.injectJavaScript(loginScript(s.naukriEmail, s.naukriPassword));
      }, 1000);
    }

    if (step === 'get_jobs') {
      setStepBoth('scraping');
      log('Recommended jobs page loaded — scraping…');
      setTimeout(() => {
        wvRef.current?.injectJavaScript(SCRAPE_JOBS_SCRIPT);
      }, 2500);
    }

    if (step === 'applying') {
      log('  Job page loaded — attempting Easy Apply…');
      setTimeout(() => {
        wvRef.current?.injectJavaScript(EASY_APPLY_SCRIPT);
      }, 2000);
    }
  }, [log, setStepBoth]);

  const handleNavChange = useCallback((nav: WebViewNavigation) => {
    const url = nav.url ?? '';

    // Login success — URL left /nlogin/
    if (
      (stepRef.current === 'filling' || stepRef.current === 'login') &&
      nav.loading === false &&
      !url.includes('/nlogin/') &&
      !url.includes('/login') &&
      url.startsWith('https://www.naukri.com')
    ) {
      log('Login successful! Fetching recommended jobs…', 'ok');
      setStepBoth('get_jobs');
      setTimeout(() => {
        wvRef.current?.injectJavaScript(`window.location.href = '${NAUKRI.RECOMMENDED}'; true;`);
      }, 500);
    }
  }, [log, setStepBoth]);

  const handleMessage = useCallback(async (e: any) => {
    try {
      const msg: BotMsg = JSON.parse(e.nativeEvent.data);

      if (msg.type === 'jobs') {
        log(`Found ${msg.jobs.length} recommended jobs`, 'ok');
        jobQueueRef.current = msg.jobs;
        jobIdxRef.current   = 0;
        setJobCount(msg.jobs.length);
        processNextJob();
      }

      if (msg.type === 'applied') {
        const job = jobQueueRef.current[jobIdxRef.current];
        log(`  → ✅ Applied to: ${job?.title}`, 'ok');
        if (job) await updateJobStatus(job.jobId || job.url, 'applied');
        resultRef.current.applied++;
        resultRef.current.total++;
        setResult({ ...resultRef.current });
        jobIdxRef.current++;
        setStepBoth('get_jobs'); // reset so next job navigation doesn't retrigger
        setTimeout(processNextJob, 2000);
      }

      if (msg.type === 'skipped') {
        const job = jobQueueRef.current[jobIdxRef.current];
        log(`  → Skipped: ${msg.reason}`);
        if (job) await updateJobStatus(job.jobId || job.url, 'manual_needed');
        resultRef.current.skipped++;
        resultRef.current.total++;
        setResult({ ...resultRef.current });
        jobIdxRef.current++;
        setStepBoth('get_jobs');
        setTimeout(processNextJob, 500);
      }

      if (msg.type === 'error') {
        log(`Error: ${msg.message}`, 'error');
      }
    } catch { /* not our message */ }
  }, [log, processNextJob, setStepBoth]);

  // ── Status label ─────────────────────────────────────────────────────────────

  const stepLabel = (s: Step) => {
    switch (s) {
      case 'login':     return '🔐 Opening login page…';
      case 'filling':   return '✏️ Filling credentials…';
      case 'logged_in': return '✅ Logged in';
      case 'get_jobs':  return '📋 Loading recommended jobs…';
      case 'scraping':  return '🔍 Scraping job list…';
      case 'applying':  return `⚡ Applying ${jobIdx + 1} / ${jobCount || '?'}`;
      case 'done':      return '✅ All done!';
      case 'error':     return '❌ Error';
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <Modal visible animationType="slide" statusBarTranslucent>
      <View style={styles.root}>

        {/* Top bar */}
        <View style={styles.topBar}>
          <View>
            <Text style={styles.topLabel}>{stepLabel(step)}</Text>
            <Text style={styles.topSub}>Naukri Bot · Recommended Jobs</Text>
          </View>
          {(step === 'done' || step === 'error') && (
            <TouchableOpacity style={styles.doneBtn} onPress={() => onClose(result)}>
              <Text style={styles.doneTxt}>Done</Text>
            </TouchableOpacity>
          )}
          {step !== 'done' && step !== 'error' && (
            <ActivityIndicator color={C.accentLight} />
          )}
        </View>

        {/* Stats row */}
        <View style={styles.statsRow}>
          <View style={[styles.statPill, { borderColor: C.green + '44' }]}>
            <Text style={[styles.statNum, { color: C.green }]}>{result.applied}</Text>
            <Text style={styles.statLbl}>Applied</Text>
          </View>
          <View style={[styles.statPill, { borderColor: C.textMuted + '44' }]}>
            <Text style={[styles.statNum, { color: C.textSub }]}>{result.skipped}</Text>
            <Text style={styles.statLbl}>Skipped</Text>
          </View>
          <View style={[styles.statPill, { borderColor: C.blue + '44' }]}>
            <Text style={[styles.statNum, { color: C.blue }]}>{jobCount || '—'}</Text>
            <Text style={styles.statLbl}>Found</Text>
          </View>
        </View>

        {/* Log pane */}
        <View style={styles.logPane}>
          <ScrollView ref={scrollRef} style={styles.logScroll} contentContainerStyle={{ padding: 8 }}>
            {logs.map((l, i) => (
              <Text key={i} style={[styles.logLine, {
                color: l.level === 'ok' ? C.green : l.level === 'error' ? C.red : l.level === 'warn' ? C.orange : C.textSub,
              }]}>
                <Text style={styles.logTs}>{l.ts} </Text>{l.msg}
              </Text>
            ))}
          </ScrollView>
        </View>

        {/* WebView — visible browser (same as Python bot BROWSER_HEADLESS=False) */}
        <WebView
          ref={wvRef}
          source={{ uri: NAUKRI.LOGIN }}
          style={styles.webView}
          javaScriptEnabled
          domStorageEnabled
          thirdPartyCookiesEnabled
          sharedCookiesEnabled
          onLoadEnd={handleLoadEnd}
          onNavigationStateChange={handleNavChange}
          onMessage={handleMessage}
          userAgent="Mozilla/5.0 (Linux; Android 12; Moto G85 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
          onError={() => log('WebView error — check network', 'error')}
        />
      </View>
    </Modal>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root:      { flex: 1, backgroundColor: C.bg },
  topBar:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
               paddingHorizontal: 16, paddingVertical: 12, paddingTop: 52,
               backgroundColor: C.card, borderBottomWidth: 1, borderBottomColor: C.border },
  topLabel:  { fontSize: 14, fontWeight: '700', color: C.text },
  topSub:    { fontSize: 11, color: C.textMuted, marginTop: 2 },
  doneBtn:   { backgroundColor: C.accent, paddingHorizontal: 18, paddingVertical: 8, borderRadius: 50 },
  doneTxt:   { color: '#fff', fontWeight: '700', fontSize: 13 },
  statsRow:  { flexDirection: 'row', gap: 10, padding: 10,
               backgroundColor: C.bgAlt, borderBottomWidth: 1, borderBottomColor: C.border },
  statPill:  { flex: 1, alignItems: 'center', paddingVertical: 6,
               backgroundColor: C.card, borderWidth: 1, borderRadius: 12 },
  statNum:   { fontSize: 20, fontWeight: '800' },
  statLbl:   { fontSize: 10, color: C.textMuted, marginTop: 1 },
  logPane:   { height: 120, backgroundColor: C.bg, borderBottomWidth: 1, borderBottomColor: C.border },
  logScroll: { flex: 1 },
  logLine:   { fontFamily: 'monospace', fontSize: 10, lineHeight: 16 },
  logTs:     { color: C.textMuted },
  webView:   { flex: 1 },
});
