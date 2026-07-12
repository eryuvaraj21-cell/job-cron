import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getBaseUrl, saveBaseUrl, testConnection, DEFAULT_BASE_URL } from '../api';
import { C } from '../theme';

export default function SettingsScreen() {
  const [url, setUrl]         = useState('');
  const [saved, setSaved]     = useState('');
  const [testing, setTesting] = useState(false);
  const [connOk, setConnOk]   = useState<boolean | null>(null);

  useEffect(() => {
    getBaseUrl().then(u => { setUrl(u); setSaved(u); });
  }, []);

  const handleSave = useCallback(async () => {
    const trimmed = url.trim();
    if (!trimmed) { Alert.alert('Invalid', 'URL cannot be empty'); return; }
    await saveBaseUrl(trimmed);
    setSaved(trimmed);
    setConnOk(null);
    Alert.alert('Saved', 'Server URL updated.');
  }, [url]);

  const handleTest = useCallback(async () => {
    if (url.trim() !== saved) {
      Alert.alert('Save first', 'Please save the URL before testing.');
      return;
    }
    setTesting(true);
    setConnOk(null);
    const ok = await testConnection();
    setConnOk(ok);
    setTesting(false);
    if (!ok) Alert.alert('Connection failed', 'Cannot reach the bot server.\nMake sure:\n• The bot is running\n• Your phone and PC are on the same Wi-Fi\n• The IP and port are correct');
  }, [url, saved]);

  const handleReset = () => {
    setUrl(DEFAULT_BASE_URL);
    setConnOk(null);
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>⚙️ Settings</Text>
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll}>

          {/* Connection card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Bot Server URL</Text>
            <Text style={styles.cardDesc}>
              Enter the URL of your PC running the job bot.{'\n'}
              Usually <Text style={{ color: C.blue }}>http://&lt;your-PC-IP&gt;:8080</Text>
            </Text>

            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                value={url}
                onChangeText={t => { setUrl(t); setConnOk(null); }}
                placeholder="http://192.168.1.100:8080"
                placeholderTextColor={C.textMuted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
              />
            </View>

            {/* Connection status */}
            {connOk !== null && (
              <View style={[styles.connStatus, { backgroundColor: connOk ? C.greenBg : C.redBg }]}>
                <Ionicons
                  name={connOk ? 'checkmark-circle' : 'close-circle'}
                  size={16}
                  color={connOk ? C.green : C.red}
                />
                <Text style={[styles.connText, { color: connOk ? C.green : C.red }]}>
                  {connOk ? 'Connected successfully' : 'Connection failed'}
                </Text>
              </View>
            )}

            <View style={styles.btnRow}>
              <TouchableOpacity style={styles.btnSecondary} onPress={handleReset}>
                <Text style={styles.btnSecondaryText}>Reset</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.btnOutline} onPress={handleTest} disabled={testing}>
                {testing
                  ? <ActivityIndicator size="small" color={C.accent} />
                  : <Ionicons name="wifi" size={15} color={C.accent} />
                }
                <Text style={styles.btnOutlineText}>Test</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.btnPrimary, url.trim() === saved && styles.btnSaved]}
                onPress={handleSave}
                disabled={url.trim() === saved}
              >
                <Ionicons name="save-outline" size={15} color="#fff" />
                <Text style={styles.btnPrimaryText}>{url.trim() === saved ? 'Saved' : 'Save'}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* How-to card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>How to connect</Text>
            {[
              { n: '1', text: 'Start the bot on your PC:  python -m src.main' },
              { n: '2', text: 'Find your PC\'s local IP (e.g. 192.168.1.xx)' },
              { n: '3', text: 'Make sure your phone & PC are on the same Wi-Fi' },
              { n: '4', text: 'Enter http://<PC-IP>:8080 above and tap Save' },
              { n: '5', text: 'Tap Test to verify the connection' },
            ].map(item => (
              <View key={item.n} style={styles.howToRow}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepNum}>{item.n}</Text>
                </View>
                <Text style={styles.howToText}>{item.text}</Text>
              </View>
            ))}
          </View>

          {/* App info */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>App info</Text>
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>Version</Text>
              <Text style={styles.infoVal}>1.0.0</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>Platform</Text>
              <Text style={styles.infoVal}>Naukri</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>Dashboard</Text>
              <Text style={styles.infoVal}>{saved || DEFAULT_BASE_URL}</Text>
            </View>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:      { flex: 1, backgroundColor: C.bg },
  header:        { paddingHorizontal: 16, paddingVertical: 12,
                   borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:   { fontSize: 18, fontWeight: '700', color: C.text },
  scroll:        { padding: 16, gap: 16, paddingBottom: 40 },
  card:          { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                   borderRadius: 16, padding: 16, gap: 12 },
  cardTitle:     { fontSize: 14, fontWeight: '700', color: C.text },
  cardDesc:      { fontSize: 12, color: C.textSub, lineHeight: 18 },
  inputRow:      { flexDirection: 'row', gap: 8 },
  input:         { flex: 1, backgroundColor: C.bg, borderWidth: 1, borderColor: C.border,
                   borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11,
                   color: C.text, fontSize: 13, fontFamily: 'monospace' },
  connStatus:    { flexDirection: 'row', alignItems: 'center', gap: 8,
                   padding: 10, borderRadius: 10 },
  connText:      { fontSize: 12, fontWeight: '600' },
  btnRow:        { flexDirection: 'row', gap: 10 },
  btnPrimary:    { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
                   gap: 6, backgroundColor: C.accent, borderRadius: 10, paddingVertical: 11 },
  btnSaved:      { backgroundColor: C.borderSoft },
  btnPrimaryText:{ color: '#fff', fontWeight: '700', fontSize: 13 },
  btnOutline:    { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
                   gap: 6, borderWidth: 1, borderColor: C.accent, borderRadius: 10, paddingVertical: 11 },
  btnOutlineText:{ color: C.accent, fontWeight: '600', fontSize: 13 },
  btnSecondary:  { paddingHorizontal: 14, paddingVertical: 11, borderWidth: 1,
                   borderColor: C.border, borderRadius: 10, justifyContent: 'center' },
  btnSecondaryText: { color: C.textSub, fontSize: 13 },
  howToRow:      { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  stepBadge:     { width: 22, height: 22, borderRadius: 11, backgroundColor: C.accent + '33',
                   alignItems: 'center', justifyContent: 'center' },
  stepNum:       { fontSize: 11, fontWeight: '700', color: C.accent },
  howToText:     { flex: 1, fontSize: 12, color: C.textSub, lineHeight: 18, paddingTop: 2 },
  infoRow:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  infoKey:       { fontSize: 12, color: C.textMuted },
  infoVal:       { fontSize: 12, color: C.textSub, fontFamily: 'monospace', flex: 1, textAlign: 'right' },
});
