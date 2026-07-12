import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert, Switch, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { runBotCycle, getRunStatus, RunStatus } from '../services/bot';
import { getStats, LocalStats } from '../services/database';
import { isScheduled, registerBackgroundFetch, unregisterBackgroundFetch } from '../services/scheduler';
import { C, fmtTime } from '../theme';

function StatCard({ label, value, color, icon }: { label: string; value: string | number; color: string; icon: any }) {
  return (
    <View style={[styles.statCard, { borderColor: color + '33' }]}>
      <View style={[styles.statIconWrap, { backgroundColor: color + '18' }]}>
        <Ionicons name={icon} size={16} color={color} />
      </View>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}


export default function DashboardScreen() {
  const [status, setStatus]       = useState<RunStatus | null>(null);
  const [stats, setStats]         = useState<LocalStats | null>(null);
  const [scheduled, setScheduled] = useState(false);
  const [running, setRunning]     = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [s, st, sch] = await Promise.all([getRunStatus(), getStats(), isScheduled()]);
    setStatus(s); setStats(st); setScheduled(sch);
  }, []);

  useEffect(() => { load(); const id = setInterval(load, 10_000); return () => clearInterval(id); }, [load]);

  const onRefresh = useCallback(async () => { setRefreshing(true); await load(); setRefreshing(false); }, [load]);

  const handleRun = useCallback(async () => {
    if (status?.running) { Alert.alert('Already running', 'A cycle is already in progress.'); return; }
    Alert.alert('Run Now', 'Start a job search cycle?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Run', onPress: async () => {
        setRunning(true);
        try {
          const { newJobs, matched } = await runBotCycle();
          Alert.alert('✅ Done', newJobs > 0 ? `Found ${newJobs} new, ${matched} matched.` : 'No new jobs.');
        } catch { Alert.alert('Error', 'Cycle failed. Check Logs tab.'); }
        finally { setRunning(false); load(); }
      }},
    ]);
  }, [status, load]);

  const toggleSchedule = useCallback(async (val: boolean) => {
    val ? await registerBackgroundFetch() : await unregisterBackgroundFetch();
    setScheduled(val);
  }, []);

  const a = stats;
  const isRunning = running || !!status?.running;
  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.logoCircle}><Text style={styles.logoEmoji}>🤖</Text></View>
          <View>
            <Text style={styles.headerTitle}>Job Bot</Text>
            <Text style={styles.headerSub}>Naukri · Auto Apply</Text>
          </View>
        </View>
        <View style={[styles.statusPill, { backgroundColor: isRunning ? C.accentBg : C.greenBg }]}>
          <View style={[styles.statusDot, { backgroundColor: isRunning ? C.accentLight : C.green }]} />
          <Text style={[styles.statusText, { color: isRunning ? C.accentLight : C.green }]}>
            {isRunning ? 'Running' : 'Ready'}
          </Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accentMid} />}>

        <View style={styles.heroCard}>
          <Text style={styles.heroTitle}>
            {isRunning ? 'Searching Naukri…' :
             status?.lastResult === 'success' ? 'Last cycle completed ✓' :
             status?.lastResult === 'never'   ? 'Ready to find jobs'     : '⚠ Last cycle had an issue'}
          </Text>
          {!!status?.lastRun && !isRunning && (
            <Text style={styles.heroSub}>Last run at {fmtTime(status.lastRun)}</Text>
          )}
          <TouchableOpacity style={[styles.runBtn, isRunning && styles.runBtnRunning]}
            onPress={handleRun} disabled={isRunning} activeOpacity={0.85}>
            <View style={styles.runBtnInner}>
              {isRunning ? <ActivityIndicator color="#fff" size={22} /> : <Ionicons name="rocket-outline" size={22} color="#fff" />}
              <Text style={styles.runBtnText}>{isRunning ? 'Running…' : 'Launch'}</Text>
            </View>
          </TouchableOpacity>
        </View>

        <View style={styles.scheduleCard}>
          <Ionicons name="time-outline" size={18} color={scheduled ? C.accentLight : C.textMuted} />
          <View style={styles.scheduleMid}>
            <Text style={styles.scheduleTitle}>Background scheduler</Text>
            <Text style={styles.scheduleSub}>{scheduled ? 'Active · runs every ~30 min' : 'Off'}</Text>
          </View>
          <Switch value={scheduled} onValueChange={toggleSchedule}
            trackColor={{ false: C.border, true: C.accentMid }} thumbColor="#fff" />
        </View>

        <Text style={styles.sectionTitle}>TODAY</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Found"   value={a?.today_total   ?? 0} color={C.blue}  icon="search-outline" />
          <StatCard label="Applied" value={a?.today_applied ?? 0} color={C.green} icon="checkmark-circle-outline" />
        </View>

        <Text style={styles.sectionTitle}>ALL TIME</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Total"   value={a?.total         ?? 0} color={C.blue}   icon="layers-outline" />
          <StatCard label="Applied" value={a?.applied       ?? 0} color={C.green}  icon="checkmark-done-outline" />
          <StatCard label="Matched" value={a?.manual_needed ?? 0} color={C.orange} icon="star-outline" />
          <StatCard label="Skipped" value={a?.skipped       ?? 0} color={C.gray}   icon="remove-circle-outline" />
        </View>

        {(a?.total ?? 0) > 0 && (
          <>
            <Text style={styles.sectionTitle}>BREAKDOWN</Text>
            <View style={styles.chartCard}>
              {[{label:'Applied',val:a?.applied??0,color:C.green},{label:'Matched',val:a?.manual_needed??0,color:C.orange},{label:'Skipped',val:a?.skipped??0,color:C.gray}]
                .map(item => (
                  <View key={item.label} style={styles.barRow}>
                    <Text style={styles.barLabel}>{item.label}</Text>
                    <View style={styles.barTrack}><View style={[styles.barFill,{backgroundColor:item.color,width:`${Math.max(2,(item.val/(a?.total||1))*100)}%`}]} /></View>
                    <Text style={[styles.barVal,{color:item.color}]}>{item.val}</Text>
                  </View>))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:       { flex: 1, backgroundColor: C.bg },
  header:         { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                    paddingHorizontal: 20, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: C.border },
  headerLeft:     { flexDirection: 'row', alignItems: 'center', gap: 12 },
  logoCircle:     { width: 38, height: 38, borderRadius: 12, backgroundColor: C.accentBg,
                    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.accent + '44' },
  logoEmoji:      { fontSize: 18 },
  headerTitle:    { fontSize: 16, fontWeight: '800', color: C.text },
  headerSub:      { fontSize: 10, color: C.textMuted, marginTop: 1 },
  statusPill:     { flexDirection: 'row', alignItems: 'center', gap: 6,
                    paddingHorizontal: 10, paddingVertical: 5, borderRadius: 50 },
  statusDot:      { width: 7, height: 7, borderRadius: 4 },
  statusText:     { fontSize: 11, fontWeight: '700' },
  scroll:         { padding: 16, paddingBottom: 32, gap: 16 },
  heroCard:       { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                    borderRadius: 20, padding: 20, alignItems: 'center', gap: 6,
                    shadowColor: C.accent, shadowOpacity: 0.08, shadowRadius: 20, elevation: 3 },
  heroTitle:      { fontSize: 16, fontWeight: '700', color: C.text, textAlign: 'center' },
  heroSub:        { fontSize: 12, color: C.textSub, marginBottom: 4 },
  runBtn:         { marginTop: 8, width: '100%', borderRadius: 16, overflow: 'hidden',
                    backgroundColor: C.accent, shadowColor: C.accent,
                    shadowOpacity: 0.45, shadowRadius: 14, elevation: 6 },
  runBtnRunning:  { opacity: 0.7 },
  runBtnInner:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
                    gap: 10, paddingVertical: 16 },
  runBtnText:     { color: '#fff', fontWeight: '800', fontSize: 16, letterSpacing: 0.5 },
  scheduleCard:   { flexDirection: 'row', alignItems: 'center', gap: 12,
                    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                    borderRadius: 16, padding: 14 },
  scheduleMid:    { flex: 1 },
  scheduleTitle:  { fontSize: 13, fontWeight: '600', color: C.text },
  scheduleSub:    { fontSize: 11, color: C.textSub, marginTop: 2 },
  sectionTitle:   { fontSize: 10, fontWeight: '700', color: C.textMuted,
                    textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: -8 },
  statsGrid:      { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  statCard:       { flex: 1, minWidth: '44%', backgroundColor: C.card, borderWidth: 1,
                    borderRadius: 18, padding: 16, gap: 8 },
  statIconWrap:   { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  statValue:      { fontSize: 30, fontWeight: '800', letterSpacing: -1 },
  statLabel:      { fontSize: 11, color: C.textSub },
  chartCard:      { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                    borderRadius: 18, padding: 16, gap: 14 },
  barRow:         { flexDirection: 'row', alignItems: 'center', gap: 10 },
  barLabel:       { width: 58, fontSize: 11, color: C.textSub },
  barTrack:       { flex: 1, height: 6, backgroundColor: C.border, borderRadius: 3, overflow: 'hidden' },
  barFill:        { height: 6, borderRadius: 3 },
  barVal:         { width: 28, textAlign: 'right', fontSize: 11, fontWeight: '700' },
});
