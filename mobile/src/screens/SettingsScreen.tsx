import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Alert, ActivityIndicator, KeyboardAvoidingView, Platform, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { loadSettings, saveSettings, BotSettings } from '../services/settings';
import { requestPermissions } from '../services/notifications';
import { clearToken } from '../services/naukri';
import NaukriLoginWebView from '../components/NaukriLoginWebView';
import { C } from '../theme';

function Field({ label, value, onChangeText, placeholder, multiline = false, keyboardType = 'default' }: {
  label: string; value: string; onChangeText: (t: string) => void;
  placeholder?: string; multiline?: boolean; keyboardType?: any;
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput style={[styles.input, multiline && styles.inputMulti]} value={value}
        onChangeText={onChangeText} placeholder={placeholder} placeholderTextColor={C.textMuted}
        autoCapitalize="none" autoCorrect={false} multiline={multiline}
        numberOfLines={multiline ? 3 : 1} keyboardType={keyboardType} />
    </View>
  );
}

export default function SettingsScreen() {
  const [settings, setSettings] = useState<BotSettings | null>(null);
  const [saving, setSaving]     = useState(false);
  const [notifOk, setNotifOk]   = useState<boolean | null>(null);
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('');
  const [skills,   setSkills]   = useState('');
  const [experience, setExperience] = useState('');
  const [minScore, setMinScore] = useState('');
  const [interval, setInterval] = useState('');
  const [pages,    setPages]    = useState('');
  const [naukriEmail,    setNaukriEmail]    = useState('');
  const [naukriPassword, setNaukriPassword] = useState('');
  const [loginStatus, setLoginStatus]       = useState<'idle' | 'testing' | 'ok' | 'fail'>('idle');
  const [showWebLogin, setShowWebLogin]     = useState(false);

  useEffect(() => {
    loadSettings().then(s => {
      setSettings(s);
      setKeywords(s.keywords.join(', '));
      setLocation(s.location);
      setSkills(s.skills.join(', '));
      setExperience(String(s.experienceYears));
      setMinScore(String(s.minMatchScore));
      setInterval(String(s.intervalMinutes));
      setPages(String(s.maxPagesPerSearch));
      setNaukriEmail(s.naukriEmail ?? '');
      setNaukriPassword(s.naukriPassword ?? '');
    });
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await saveSettings({
        keywords:          keywords.split(',').map(k => k.trim()).filter(Boolean),
        location:          location.trim(),
        skills:            skills.split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
        experienceYears:   parseInt(experience) || 4,
        minMatchScore:     parseInt(minScore)   || 30,
        intervalMinutes:   parseInt(interval)   || 30,
        maxPagesPerSearch: parseInt(pages)       || 3,
        naukriEmail:       naukriEmail.trim(),
        naukriPassword:    naukriPassword,
        useRecommended:    true,
      });
      Alert.alert('Saved', 'Settings saved. Changes take effect on next run.');
    } catch { Alert.alert('Error', 'Could not save.'); }
    finally { setSaving(false); }
  }, [keywords, location, skills, experience, minScore, interval, pages, naukriEmail, naukriPassword]);

  if (!settings) return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.center}><ActivityIndicator color={C.accent} /></View>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}><Text style={styles.headerTitle}>⚙️ Settings</Text></View>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll}>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>🔍 Job Search</Text>
            <Field label="Search keywords (comma-separated)" value={keywords} onChangeText={setKeywords}
              placeholder="node.js developer, backend developer" multiline />
            <Field label="Location" value={location} onChangeText={setLocation} placeholder="bangalore" />
            <Field label="Experience (years)" value={experience} onChangeText={setExperience} placeholder="4" keyboardType="number-pad" />
            <Field label="Pages per search (1–5)" value={pages} onChangeText={setPages} placeholder="3" keyboardType="number-pad" />
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>🛠 My Skills</Text>
            <Text style={styles.cardDesc}>Comma-separated. Used to score how well a job matches you.</Text>
            <Field label="Skills" value={skills} onChangeText={setSkills}
              placeholder="javascript, node.js, mongodb, docker" multiline />
            <Field label="Min match score (0–100)" value={minScore} onChangeText={setMinScore} placeholder="30" keyboardType="number-pad" />
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>🔐 Naukri Account</Text>
            <Text style={styles.cardDesc}>
              Enter your Naukri credentials to enable personalised recommended jobs (same as the Python bot). Leave blank to use public search only.
            </Text>
            <Field label="Naukri Email" value={naukriEmail} onChangeText={e => { setNaukriEmail(e); setLoginStatus('idle'); }}
              placeholder="eryuvaraj21@gmail.com" keyboardType="email-address" />
            <Field label="Naukri Password" value={naukriPassword} onChangeText={p => { setNaukriPassword(p); setLoginStatus('idle'); }}
              placeholder="Your Naukri password" />
            <TouchableOpacity
              style={[styles.notifBtn, loginStatus === 'ok' && { borderColor: C.green }, loginStatus === 'fail' && { borderColor: C.red }]}
              disabled={loginStatus === 'testing'}
              onPress={async () => {
                if (!naukriEmail || !naukriPassword) { Alert.alert('Missing', 'Enter email and password first.'); return; }
                await clearToken();
                setLoginStatus('testing');
                setShowWebLogin(true);
              }}>
              {loginStatus === 'testing'
                ? <ActivityIndicator size="small" color={C.accentLight} />
                : <Ionicons name={loginStatus === 'ok' ? 'checkmark-circle' : loginStatus === 'fail' ? 'close-circle' : 'log-in-outline'}
                    size={18} color={loginStatus === 'ok' ? C.green : loginStatus === 'fail' ? C.red : C.accentLight} />}
              <Text style={[styles.notifBtnText, {
                color: loginStatus === 'ok' ? C.green : loginStatus === 'fail' ? C.red : C.accentLight
              }]}>
                {loginStatus === 'testing' ? 'Opening browser login…' : loginStatus === 'ok' ? 'Connected' : loginStatus === 'fail' ? 'Login failed' : 'Login via Naukri browser'}
              </Text>
            </TouchableOpacity>

            {showWebLogin && (
              <NaukriLoginWebView
                email={naukriEmail}
                password={naukriPassword}
                onSuccess={(token) => {
                  setShowWebLogin(false);
                  setLoginStatus('ok');
                  Alert.alert('✅ Login OK', 'Naukri session saved. Recommended jobs will be fetched on next run.');
                }}
                onError={(msg) => {
                  setShowWebLogin(false);
                  setLoginStatus('fail');
                  Alert.alert('❌ Login Failed', msg);
                }}
                onClose={() => {
                  setShowWebLogin(false);
                  setLoginStatus('idle');
                }}
              />
            )}
          </View>

          <View style={styles.card}>
            <Field label="Background run interval (minutes)" value={interval} onChangeText={setInterval} placeholder="30" keyboardType="number-pad" />
            <Text style={styles.cardDesc}>Android limits background tasks to ~15 min minimum.</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>🔔 Notifications</Text>
            <TouchableOpacity style={styles.notifBtn} onPress={async () => {
              const ok = await requestPermissions(); setNotifOk(ok);
              Alert.alert(ok ? '✅ Granted' : '❌ Denied', ok ? 'Notifications enabled.' : 'Enable in phone Settings.');
            }}>
              <Ionicons name={notifOk === true ? 'checkmark-circle' : notifOk === false ? 'close-circle' : 'notifications-outline'}
                size={18} color={notifOk === true ? C.green : notifOk === false ? C.red : C.accent} />
              <Text style={[styles.notifBtnText, { color: notifOk === true ? C.green : notifOk === false ? C.red : C.accent }]}>
                {notifOk === true ? 'Notifications enabled' : notifOk === false ? 'Permission denied' : 'Enable notifications'}
              </Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.saveBtn} onPress={handleSave} disabled={saving} activeOpacity={0.8}>
            {saving ? <ActivityIndicator color="#fff" size="small" /> : <Ionicons name="save-outline" size={18} color="#fff" />}
            <Text style={styles.saveBtnText}>{saving ? 'Saving…' : 'Save Settings'}</Text>
          </TouchableOpacity>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>ℹ️ App info</Text>
            {[['Version','1.0.0'],['Mode','Standalone (no PC required)'],['Platform','Naukri.com'],['Storage','Local SQLite on device']].map(([k,v])=>(
              <View key={k} style={styles.infoRow}><Text style={styles.infoKey}>{k}</Text><Text style={styles.infoVal}>{v}</Text></View>
            ))}
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:      { flex: 1, backgroundColor: C.bg },
  header:        { paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:   { fontSize: 18, fontWeight: '700', color: C.text },
  center:        { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll:        { padding: 16, gap: 16, paddingBottom: 40 },
  card:          { backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16, gap: 12 },
  cardTitle:     { fontSize: 14, fontWeight: '700', color: C.text },
  cardDesc:      { fontSize: 12, color: C.textSub, lineHeight: 18 },
  fieldWrap:     { gap: 6 },
  fieldLabel:    { fontSize: 12, color: C.textSub, fontWeight: '500' },
  input:         { backgroundColor: C.bg, borderWidth: 1, borderColor: C.border, borderRadius: 10,
                   paddingHorizontal: 14, paddingVertical: 10, color: C.text, fontSize: 13 },
  inputMulti:    { minHeight: 72, textAlignVertical: 'top' },
  notifBtn:      { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.bg,
                   borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12 },
  notifBtnText:  { fontWeight: '600', fontSize: 13 },
  saveBtn:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
                   backgroundColor: C.accent, borderRadius: 50, paddingVertical: 14,
                   shadowColor: C.accent, shadowOpacity: 0.35, shadowRadius: 10, elevation: 4 },
  saveBtnText:   { color: '#fff', fontWeight: '700', fontSize: 15 },
  infoRow:       { flexDirection: 'row', justifyContent: 'space-between' },
  infoKey:       { fontSize: 12, color: C.textMuted },
  infoVal:       { fontSize: 12, color: C.textSub, flex: 1, textAlign: 'right' },
});
