/**
 * Naukri HTTP client.
 * Mirrors the Python bot's scraping logic but uses HTTP instead of Selenium.
 * Supports:
 *  - Authenticated login (username + password)
 *  - Recommended jobs feed (personalized, requires login)
 *  - Public keyword search (no login)
 */
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE   = 'https://www.naukri.com';
const HEADERS = {
  'appid':      '109',
  'systemid':   '109',
  'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
  'Accept':     'application/json, text/plain, */*',
  'Referer':    'https://www.naukri.com/',
};

const AUTH_KEY = 'naukri_auth_token';

// ── Auth token cache ──────────────────────────────────────────────────────────

export async function getStoredToken(): Promise<string | null> {
  return AsyncStorage.getItem(AUTH_KEY);
}

export async function storeToken(token: string): Promise<void> {
  await AsyncStorage.setItem(AUTH_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(AUTH_KEY);
}

// ── Login ─────────────────────────────────────────────────────────────────────

/**
 * Authenticate with Naukri.
 * Uses the same API endpoint that https://www.naukri.com/nlogin/login calls.
 * Returns { token } on success or { error } on failure — never silent.
 */
export async function loginNaukri(
  email: string,
  password: string,
): Promise<{ token: string; error: null } | { token: null; error: string }> {
  if (!email || !password)
    return { token: null, error: 'Email and password are required' };

  // Headers that replicate what the browser sends from nlogin/login
  const loginHeaders = {
    'appid':          '109',
    'systemid':       'Naukri',
    'clientid':       'd3skt0p',
    'Content-Type':   'application/json',
    'Accept':         'application/json, text/plain, */*',
    'Referer':        `${BASE}/nlogin/login`,
    'Origin':         BASE,
    'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  };

  // Try primary endpoint (used by the nlogin/login page)
  const endpoints = [
    { url: `${BASE}/central-login-services/v2/login`,        body: { username: email, password } },
    { url: `${BASE}/central-login-services/v1/login`,        body: { username: email, password } },
  ];

  for (const { url, body } of endpoints) {
    try {
      const resp = await axios.post(url, body, {
        headers: loginHeaders,
        timeout: 20_000,
        validateStatus: () => true, // don't throw on 4xx — handle manually
      });

      // Extract token from wherever Naukri puts it
      const d = resp.data ?? {};
      const token =
        d?.loginResult?.clientData?.authToken ??
        d?.loginResult?.authToken ??
        d?.authToken ??
        d?.jdToken ??
        resp.headers?.['x-auth-token'] ??
        resp.headers?.['authtoken'] ??
        null;

      if (token) {
        await storeToken(token);
        return { token, error: null };
      }

      // Login succeeded HTTP-wise but no token — surface the message
      if (resp.status === 200 && !token) {
        const msg = d?.message ?? d?.error ?? 'Login response contained no token';
        return { token: null, error: `HTTP 200 but no token: ${msg}` };
      }

      if (resp.status === 401 || resp.status === 403) {
        const msg = d?.message ?? d?.error ?? 'Invalid credentials';
        return { token: null, error: `HTTP ${resp.status}: ${msg}` };
      }

    } catch (err: any) {
      // Only continue to the next endpoint on network-level errors
      if (!err?.response) continue;
      return { token: null, error: err.message ?? String(err) };
    }
  }

  return { token: null, error: 'All login endpoints failed — check your internet connection' };
}

// ── Job shape ─────────────────────────────────────────────────────────────────

export interface NaukriJob {
  jobId:       string;
  title:       string;
  company:     string;
  location:    string;
  url:         string;
  description: string;
  skills:      string[];
  experience:  string;
}

interface ApiJob {
  jobId?: string;
  title?: string;
  companyName?: string;
  placeholders?: Array<{ label?: string; title?: string }>;
  jdURL?: string;
  jobDescription?: string;
  tagsAndSkills?: string;
  reqExp?: string;
}

function parseJob(raw: ApiJob): NaukriJob | null {
  if (!raw.jobId || !raw.title) return null;
  const location = raw.placeholders?.find(p => p.label === 'location')?.title ?? '';
  const skills   = (raw.tagsAndSkills ?? '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  const url      = raw.jdURL
    ? (raw.jdURL.startsWith('http') ? raw.jdURL : `${BASE}${raw.jdURL}`)
    : `${BASE}/jobs/${raw.jobId}`;
  return {
    jobId: raw.jobId, title: raw.title, company: raw.companyName ?? '',
    location, url, description: raw.jobDescription ?? '', skills,
    experience: raw.reqExp ?? '',
  };
}

// ── Recommended jobs (requires login) ────────────────────────────────────────

/**
 * Fetch personalised recommended jobs from Naukri.
 * Mirrors the Python bot's get_recommended_jobs().
 * Falls back to empty array if auth fails.
 */
export async function getRecommendedJobs(authToken: string, pages = 5): Promise<NaukriJob[]> {
  const jobs: NaukriJob[] = [];
  for (let page = 1; page <= pages; page++) {
    try {
      const resp = await axios.get(`${BASE}/jobapi/v4/jobs/recommended`, {
        headers: {
          ...HEADERS,
          'Authorization': authToken,
          'x-auth-token':  authToken,
        },
        params: { pageNo: page, noOfResults: 20 },
        timeout: 15_000,
      });
      const details: ApiJob[] =
        resp.data?.data?.jobDetails ??
        resp.data?.jobDetails ??
        [];
      if (!details.length) break;
      for (const d of details) {
        const j = parseJob(d);
        if (j) jobs.push(j);
      }
    } catch {
      break;
    }
  }
  return jobs;
}

// ── Public search (no login needed) ──────────────────────────────────────────

export async function searchNaukri(
  keyword: string,
  location: string,
  experience: number,
  pages = 3,
  authToken?: string,
): Promise<NaukriJob[]> {
  const jobs: NaukriJob[] = [];
  const extraHeaders = authToken
    ? { Authorization: authToken, 'x-auth-token': authToken }
    : {};

  for (let page = 1; page <= pages; page++) {
    try {
      const resp = await axios.get(`${BASE}/jobapi/v3/search`, {
        headers: { ...HEADERS, ...extraHeaders },
        params: {
          noOfResults: 20,
          urlType:     'search_by_keyword',
          searchType:  'adv',
          keyword,
          location,
          pageNo:      page,
          experience,
        },
        timeout: 15_000,
      });
      const details: ApiJob[] = resp.data?.data?.jobDetails ?? [];
      if (!details.length) break;
      for (const d of details) {
        const j = parseJob(d);
        if (j) jobs.push(j);
      }
    } catch {
      break;
    }
  }
  return jobs;
}
