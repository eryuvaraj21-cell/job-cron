import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { fetchStatus, fetchStats, triggerRun, BotStatus, StatsPayload } from '../api';
import { C, fmtTime } from '../theme';

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({
  label, value, color,
}: { label: string; value: string | number; color: string }) {
  return (
    <View style={[styles.statCard, { borderColor: C.border }]}>
      <Text style={[styles.statLabel, { color: C.textSub }]}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

function StatusBanner({ status }: { status: BotStatus | null }) {
  if (!status) return null;
  let icon: any = 'time-outline';
  let title = 'Loading…';
  let sub = '';
  let iconColor = C.textMuted;

  if (status.running) {
    icon = 'sync'; iconColor = C.accent;
    title = 'Cycle running…'; sub = 'Bot is scraping and applying';
  } else if (status.last_run_result === 'never') {
    icon = 'moon-outline'; iconColor = C.textMuted;
    title = 'Idle — never run'; sub = 'Tap Run Now to start';
  } else if (status.last_run_result === 'success') {
    icon = 'checkmark-circle'; iconColor = C.green;
    title = 'Last cycle succeeded'; sub = 'at ' + fmtTime(status.last_run);
  } else {
    icon = 'alert-circle'; iconColor = C.red;
    title = 'Last cycle had an error'; sub = status.last_run_result;
  }

  return (
    <View style={styles.banner}>
      <Ionicons name={icon} size={28} color={iconColor} />
      <View style={{ flex: 1, marginLeft: 12 }}>
        <Text style={[styles.bannerTitle, { color: C.text }]}>{title}</Text>
        {!!sub && <Text style={[styles.bannerSub, { color: C.textSub }]}>{sub}</Text>}
      </View>
    </View>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function DashboardScreen() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [stats, setStats]   = useState<StatsPayload | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, st] = await Promise.all([fetchStatus(), fetchStats()]);
      setStatus(s);
      setStats(st);
    } catch { /* network offline — keep showing last values */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const handleRun = useCallback(async () => {
    if (status?.running) {
      Alert.alert('Already running', 'A job cycle is already in progress.');
      return;
    }
    Alert.alert('Run Now', 'Trigger a job scrape & apply cycle?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Run', style: 'default',
        onPress: async () => {
          setRunning(true);
          try {
            const res = await triggerRun();
            Alert.alert(res.ok ? '✅ Started' : '⚠️ Warning', res.message);
            setTimeout(load, 2000);
          } catch {
            Alert.alert('Error', 'Could not reach the bot server. Check Settings.');
          } finally {
            setRunning(false);
          }
        },
      },
    ]);
  }, [status, load]);

  const t  = stats?.today    ?? {};
  const a  = stats?.all_time ?? { total: 0, applied: 0, manual_needed: 0, skipped: 0, failed: 0 };
  const todayTotal = Object.values(t).reduce((s, v) => s + v, 0);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🤖 Job Bot</Text>
        <View style={[
          styles.onlineDot,
          { backgroundColor: status?.running ? C.accent : (status ? C.green : C.textMuted) },
        ]} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
      >
        <StatusBanner status={status} />

        {/* Run button */}
        <TouchableOpacity
          style={[styles.runBtn, (running || status?.running) && styles.runBtnDisabled]}
          onPress={handleRun}
          disabled={running || !!status?.running}
          activeOpacity={0.8}
        >
          {running
            ? <ActivityIndicator color="#fff" size="small" />
            : <Ionicons name="play" size={18} color="#fff" />
          }
          <Text style={styles.runBtnText}>{running ? 'Starting…' : 'Run Now'}</Text>
        </TouchableOpacity>

        {/* Stats grid */}
        <Text style={styles.sectionTitle}>Today · {stats?.date ?? '—'}</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Applied today"  value={t.applied ?? 0}        color={C.green}  />
          <StatCard label="Jobs found"     value={todayTotal}             color={C.blue}   />
          <StatCard label="Manual needed"  value={t.manual_needed ?? 0}  color={C.orange} />
          <StatCard label="Skipped today"  value={t.skipped ?? 0}        color={C.gray}   />
        </View>

        <Text style={styles.sectionTitle}>All time</Text>
        <View style={styles.statsGrid}>
          <StatCard label="Total applied"  value={a.applied ?? 0}        color={C.green}  />
          <StatCard label="Total found"    value={a.total ?? 0}          color={C.blue}   />
          <StatCard label="Manual needed"  value={a.manual_needed ?? 0}  color={C.orange} />
          <StatCard label="Failed"         value={a.failed ?? 0}         color={C.red}    />
        </View>

        {/* Bar chart */}
        {a.total > 0 && (
          <>
            <Text style={styles.sectionTitle}>Breakdown</Text>
            <View style={styles.chartCard}>
              {[
                { label: 'Applied',       val: a.applied ?? 0,        color: C.green  },
                { label: 'Manual needed', val: a.manual_needed ?? 0,  color: C.orange },
                { label: 'Skipped',       val: a.skipped ?? 0,        color: C.gray   },
                { label: 'Failed',        val: a.failed ?? 0,         color: C.red    },
              ].map(item => (
                <View key={item.label} style={styles.barRow}>
                  <Text style={styles.barLabel}>{item.label}</Text>
                  <View style={styles.barTrack}>
                    <View style={[
                      styles.barFill,
                      {
                        backgroundColor: item.color,
                        width: `${Math.max(2, (item.val / (a.total || 1)) * 100)}%`,
                      },
                    ]} />
                  </View>
                  <Text style={[styles.barVal, { color: item.color }]}>{item.val}</Text>
                </View>
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:         { flex: 1, backgroundColor: C.bg },
  header:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                      paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:      { fontSize: 18, fontWeight: '700', color: C.text },
  onlineDot:        { width: 10, height: 10, borderRadius: 5 },
  scroll:           { padding: 16, gap: 16, paddingBottom: 32 },
  banner:           { flexDirection: 'row', alignItems: 'center', backgroundColor: C.card,
                      borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16 },
  bannerTitle:      { fontSize: 14, fontWeight: '600' },
  bannerSub:        { fontSize: 12, marginTop: 2 },
  runBtn:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
                      backgroundColor: C.accent, borderRadius: 50, paddingVertical: 14,
                      paddingHorizontal: 24, shadowColor: C.accent, shadowOpacity: 0.35,
                      shadowRadius: 10, elevation: 4 },
  runBtnDisabled:   { opacity: 0.6 },
  runBtnText:       { color: '#fff', fontWeight: '700', fontSize: 15 },
  sectionTitle:     { fontSize: 12, fontWeight: '600', color: C.textMuted, textTransform: 'uppercase',
                      letterSpacing: 0.8, marginBottom: -8 },
  statsGrid:        { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  statCard:         { flex: 1, minWidth: '44%', backgroundColor: C.card, borderWidth: 1,
                      borderRadius: 16, padding: 16 },
  statLabel:        { fontSize: 11, marginBottom: 6 },
  statValue:        { fontSize: 28, fontWeight: '800' },
  chartCard:        { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                      borderRadius: 16, padding: 16, gap: 14 },
  barRow:           { flexDirection: 'row', alignItems: 'center', gap: 10 },
  barLabel:         { width: 96, fontSize: 12, color: C.textSub },
  barTrack:         { flex: 1, height: 8, backgroundColor: C.border, borderRadius: 4, overflow: 'hidden' },
  barFill:          { height: 8, borderRadius: 4 },
  barVal:           { width: 32, textAlign: 'right', fontSize: 12, fontWeight: '600' },
});
