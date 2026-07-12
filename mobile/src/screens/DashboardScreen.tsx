import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { runBotCycle, getRunStatus, RunStatus } from '../services/bot';
import { getStats, LocalStats } from '../services/database';
import { isScheduled, registerBackgroundFetch, unregisterBackgroundFetch } from '../services/scheduler';
import { C, fmtTime } from '../theme';

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <View style={[styles.statCard, { borderColor: C.border }]}>
      <Text style={[styles.statLabel, { color: C.textSub }]}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
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
  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🤖 Job Bot</Text>
        <View style={[styles.onlineDot, { backgroundColor: status?.running ? C.accent : C.green }]} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}>

        <View style={styles.banner}>
          <Ionicons name={status?.running ? 'sync' : status?.lastResult === 'success' ? 'checkmark-circle' : status?.lastResult === 'never' ? 'moon-outline' : 'alert-circle'}
            size={28} color={status?.running ? C.accent : status?.lastResult === 'success' ? C.green : status?.lastResult === 'never' ? C.textMuted : C.red} />
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={[styles.bannerTitle, { color: C.text }]}>
              {status?.running ? 'Cycle running…' : status?.lastResult === 'success' ? 'Last cycle succeeded' : status?.lastResult === 'never' ? 'Never run — tap Run Now' : 'Last cycle had an error'}
            </Text>
            {!!status?.lastRun && !status.running && <Text style={[styles.bannerSub, { color: C.textSub }]}>at {fmtTime(status.lastRun)}</Text>}
          </View>
        </View>

        <TouchableOpacity style={[styles.runBtn, (running || status?.running) && styles.runBtnDisabled]}
          onPress={handleRun} disabled={running || !!status?.running} activeOpacity={0.8}>
          {(running || status?.running) ? <ActivityIndicator color="#fff" size="small" /> : <Ionicons name="play" size={18} color="#fff" />}
          <Text style={styles.runBtnText}>{(running || status?.running) ? 'Running…' : 'Run Now'}</Text>
        </TouchableOpacity>

        <View style={styles.scheduleRow}>
          <View>
            <Text style={[styles.scheduleTitle, { color: C.text }]}>Auto-run in background</Text>
            <Text style={[styles.scheduleSub, { color: C.textSub }]}>{scheduled ? 'Active — runs every ~30 min' : 'Off — tap to enable'}</Text>
          </View>
          <Switch value={scheduled} onValueChange={toggleSchedule} trackColor={{ false: C.border, true: C.accent }} thumbColor="#fff" />
        </View>

        <Text style={styles.sectionTitle}>Today</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Jobs found" value={a?.today_total ?? 0}  color={C.blue}  />
          <StatCard label="Applied"    value={a?.today_applied ?? 0} color={C.green} />
        </View>
        <Text style={styles.sectionTitle}>All time</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Total found"   value={a?.total         ?? 0} color={C.blue}   />
          <StatCard label="Applied"       value={a?.applied       ?? 0} color={C.green}  />
          <StatCard label="Manual needed" value={a?.manual_needed ?? 0} color={C.orange} />
          <StatCard label="Skipped"       value={a?.skipped       ?? 0} color={C.gray}   />
        </View>

        {(a?.total ?? 0) > 0 && (
          <><Text style={styles.sectionTitle}>Breakdown</Text>
          <View style={styles.chartCard}>
            {[{label:'Applied',val:a?.applied??0,color:C.green},{label:'Matched',val:a?.manual_needed??0,color:C.orange},{label:'Skipped',val:a?.skipped??0,color:C.gray}]
              .map(item => (
                <View key={item.label} style={styles.barRow}>
                  <Text style={styles.barLabel}>{item.label}</Text>
                  <View style={styles.barTrack}><View style={[styles.barFill,{backgroundColor:item.color,width:`${Math.max(2,(item.val/(a?.total||1))*100)}%`}]} /></View>
                  <Text style={[styles.barVal,{color:item.color}]}>{item.val}</Text>
                </View>))}
          </View></>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:       { flex: 1, backgroundColor: C.bg },
  header:         { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                    paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:    { fontSize: 18, fontWeight: '700', color: C.text },
  onlineDot:      { width: 10, height: 10, borderRadius: 5 },
  scroll:         { padding: 16, gap: 16, paddingBottom: 32 },
  banner:         { flexDirection: 'row', alignItems: 'center', backgroundColor: C.card,
                    borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16 },
  bannerTitle:    { fontSize: 14, fontWeight: '600' },
  bannerSub:      { fontSize: 12, marginTop: 2 },
  runBtn:         { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
                    backgroundColor: C.accent, borderRadius: 50, paddingVertical: 14,
                    paddingHorizontal: 24, shadowColor: C.accent, shadowOpacity: 0.35,
                    shadowRadius: 10, elevation: 4 },
  runBtnDisabled: { opacity: 0.6 },
  runBtnText:     { color: '#fff', fontWeight: '700', fontSize: 15 },
  scheduleRow:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                    borderRadius: 16, padding: 16 },
  scheduleTitle:  { fontSize: 14, fontWeight: '600', marginBottom: 2 },
  scheduleSub:    { fontSize: 12 },
  sectionTitle:   { fontSize: 12, fontWeight: '600', color: C.textMuted, textTransform: 'uppercase',
                    letterSpacing: 0.8, marginBottom: -8 },
  statsGrid:      { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  statCard:       { flex: 1, minWidth: '44%', backgroundColor: C.card, borderWidth: 1,
                    borderRadius: 16, padding: 16 },
  statLabel:      { fontSize: 11, marginBottom: 6 },
  statValue:      { fontSize: 28, fontWeight: '800' },
  chartCard:      { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                    borderRadius: 16, padding: 16, gap: 14 },
  barRow:         { flexDirection: 'row', alignItems: 'center', gap: 10 },
  barLabel:       { width: 72, fontSize: 12, color: C.textSub },
  barTrack:       { flex: 1, height: 8, backgroundColor: C.border, borderRadius: 4, overflow: 'hidden' },
  barFill:        { height: 8, borderRadius: 4 },
  barVal:         { width: 32, textAlign: 'right', fontSize: 12, fontWeight: '600' },
});
