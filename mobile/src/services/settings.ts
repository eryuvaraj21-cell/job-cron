import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'bot_settings_v2';

export interface BotSettings {
  keywords:          string[];
  location:          string;
  skills:            string[];
  experienceYears:   number;
  minMatchScore:     number;
  intervalMinutes:   number;
  maxPagesPerSearch: number;
  // Naukri account (enables recommended-jobs feed & authenticated search)
  naukriEmail:       string;
  naukriPassword:    string;
  useRecommended:    boolean;  // true = fetch recommended jobs (requires login)
}

const DEFAULTS: BotSettings = {
  keywords:          ['node.js developer', 'backend developer'],
  location:          'bangalore',
  skills:            ['javascript', 'typescript', 'node.js', 'express', 'mongodb', 'react', 'rest api', 'docker'],
  experienceYears:   4,
  minMatchScore:     30,
  intervalMinutes:   30,
  maxPagesPerSearch: 3,
  naukriEmail:       '',
  naukriPassword:    '',
  useRecommended:    true,
};

export async function loadSettings(): Promise<BotSettings> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export async function saveSettings(s: Partial<BotSettings>): Promise<void> {
  const current = await loadSettings();
  await AsyncStorage.setItem(KEY, JSON.stringify({ ...current, ...s }));
}
