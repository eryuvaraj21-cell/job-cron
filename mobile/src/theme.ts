export const C = {
  // Surfaces
  bg:         '#030712',
  card:       '#111827',
  cardAlt:    '#0f172a',
  border:     '#1f2937',
  borderSoft: '#374151',

  // Text
  text:       '#f9fafb',
  textSub:    '#9ca3af',
  textMuted:  '#6b7280',

  // Accent
  accent:     '#6366f1',
  accentDark: '#4f46e5',

  // Semantics
  green:      '#4ade80',
  greenBg:    '#14532d33' as string,
  orange:     '#fb923c',
  orangeBg:   '#7c2d1233' as string,
  red:        '#f87171',
  redBg:      '#7f1d1d33' as string,
  blue:       '#60a5fa',
  blueBg:     '#1e3a5f33' as string,
  gray:       '#a1a1aa',
  grayBg:     '#3f3f4633' as string,
};

export function statusColor(status: string): string {
  switch (status) {
    case 'applied':       return C.green;
    case 'manual_needed': return C.orange;
    case 'failed':        return C.red;
    case 'matched':       return C.blue;
    default:              return C.gray;
  }
}

export function statusBg(status: string): string {
  switch (status) {
    case 'applied':       return C.greenBg;
    case 'manual_needed': return C.orangeBg;
    case 'failed':        return C.redBg;
    case 'matched':       return C.blueBg;
    default:              return C.grayBg;
  }
}

export function logColor(msg: string): string {
  if (msg.includes('ERROR'))   return C.red;
  if (msg.includes('WARNING')) return C.orange;
  if (msg.includes('INFO'))    return '#d1d5db';
  return C.textMuted;
}

export function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

export function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch { return iso; }
}
