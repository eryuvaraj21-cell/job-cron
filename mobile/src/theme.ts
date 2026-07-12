export const C = {
  // Backgrounds
  bg:         '#070711',
  bgAlt:      '#0c0c1a',
  card:       '#0f0f1e',
  cardHover:  '#141428',
  border:     '#1c1c35',
  borderSoft: '#242445',

  // Text
  text:       '#f0f0ff',
  textSub:    '#8b8bba',
  textMuted:  '#4a4a7a',

  // Accent – purple/indigo
  accent:     '#7c3aed',
  accentMid:  '#8b5cf6',
  accentLight:'#a78bfa',
  accentBg:   '#7c3aed22',

  // Semantic
  green:      '#10b981',
  greenBg:    '#10b98122',
  orange:     '#f59e0b',
  orangeBg:   '#f59e0b22',
  red:        '#ef4444',
  redBg:      '#ef444422',
  blue:       '#3b82f6',
  blueBg:     '#3b82f622',
  gray:       '#6b7280',
  grayBg:     '#6b728022',
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
  if (msg.includes('INFO'))    return '#c4c4e8';
  return C.textMuted;
}

export function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}

export function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' }); }
  catch { return iso; }
}
