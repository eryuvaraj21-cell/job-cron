import { NaukriJob } from './naukri';

export function scoreJob(job: NaukriJob, userSkills: string[]): number {
  if (!job.skills.length && !job.description) return 0;

  const jobSkills = [
    ...job.skills,
    ...extractSkillsFromText(job.description),
  ].map(s => s.toLowerCase());

  const lower = userSkills.map(s => s.toLowerCase());
  let matched = 0;

  for (const us of lower) {
    for (const js of jobSkills) {
      if (js.includes(us) || us.includes(js)) {
        matched++;
        break;
      }
    }
  }

  const base = lower.length > 0 ? Math.round((matched / lower.length) * 100) : 0;

  // Small boost if title contains a user skill or keyword
  const titleLower = job.title.toLowerCase();
  const titleBonus = lower.some(s => titleLower.includes(s)) ? 10 : 0;

  return Math.min(100, base + titleBonus);
}

const TECH_KEYWORDS = [
  'javascript','typescript','node.js','nodejs','react','angular','vue',
  'express','fastapi','django','flask','spring','java','python','golang',
  'mongodb','postgresql','mysql','redis','docker','kubernetes','aws','azure',
  'gcp','git','rest','graphql','microservices','jest','webpack','git',
];

function extractSkillsFromText(text: string): string[] {
  const lower = text.toLowerCase();
  return TECH_KEYWORDS.filter(k => lower.includes(k));
}
