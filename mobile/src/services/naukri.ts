/**
 * Naukri HTTP client — no browser, no login required.
 * Uses Naukri's public job search API directly.
 */
import axios from 'axios';

const BASE = 'https://www.naukri.com';
const HEADERS = {
  'appid': '109',
  'systemid': '109',
  'User-Agent':
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
  'Accept': 'application/json, text/plain, */*',
  'Referer': 'https://www.naukri.com/',
};

export interface NaukriJob {
  jobId: string;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  skills: string[];
  experience: string;
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
  const location =
    raw.placeholders?.find(p => p.label === 'location')?.title ?? '';
  const skills = (raw.tagsAndSkills ?? '')
    .split(',')
    .map(s => s.trim().toLowerCase())
    .filter(Boolean);
  const url = raw.jdURL
    ? (raw.jdURL.startsWith('http') ? raw.jdURL : `${BASE}${raw.jdURL}`)
    : `${BASE}/jobs/${raw.jobId}`;
  return {
    jobId: raw.jobId,
    title: raw.title,
    company: raw.companyName ?? '',
    location,
    url,
    description: raw.jobDescription ?? '',
    skills,
    experience: raw.reqExp ?? '',
  };
}

export async function searchNaukri(
  keyword: string,
  location: string,
  experience: number,
  pages = 3,
): Promise<NaukriJob[]> {
  const jobs: NaukriJob[] = [];

  for (let page = 1; page <= pages; page++) {
    try {
      const resp = await axios.get(`${BASE}/jobapi/v3/search`, {
        headers: HEADERS,
        params: {
          noOfResults: 20,
          urlType: 'search_by_keyword',
          searchType: 'adv',
          keyword,
          location,
          pageNo: page,
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
