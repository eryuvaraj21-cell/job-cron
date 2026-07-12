import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, Linking, ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getJobs, LocalJob, updateJobStatus } from '../services/database';
import { C, statusColor, statusBg, fmtDate } from '../theme';

const FILTERS = ['all', 'applied', 'manual_needed', 'failed', 'skipped'] as const;
type Filter = typeof FILTERS[number];

// ── Job card ───────────────────────────────────────────────────────────────────

function JobCard({ job }: { job: LocalJob }) {
  const openUrl = () => {
    if (job.url) Linking.openURL(job.url).catch(() => {});
  };

  return (
    <TouchableOpacity style={styles.card} onPress={openUrl} activeOpacity={0.75}>
      <View style={styles.cardTop}>
        <Text style={styles.cardTitle} numberOfLines={2}>{job.title}</Text>
        <View style={[styles.badge, { backgroundColor: statusBg(job.status) }]}>
          <Text style={[styles.badgeText, { color: statusColor(job.status) }]}>
            {job.status.replace('_', ' ')}
          </Text>
        </View>
      </View>

      <Text style={styles.cardCompany} numberOfLines={1}>
        {[job.company, job.location].filter(Boolean).join(' · ') || '—'}
      </Text>

      <View style={styles.cardMeta}>
        <View style={styles.metaChip}>
          <Ionicons name="trophy-outline" size={11} color={C.accent} />
          <Text style={styles.metaText}>{Math.round(job.match_score ?? 0)}% match</Text>
        </View>
        <View style={styles.metaChip}>
          <Ionicons name="calendar-outline" size={11} color={C.textMuted} />
          <Text style={styles.metaText}>{fmtDate(job.discovered_at)}</Text>
        </View>
        {job.applied_at && (
          <View style={styles.metaChip}>
            <Ionicons name="checkmark-circle-outline" size={11} color={C.green} />
            <Text style={[styles.metaText, { color: C.green }]}>{fmtDate(job.applied_at)}</Text>
          </View>
        )}
        <Ionicons name="open-outline" size={13} color={C.textMuted} style={{ marginLeft: 'auto' }} />
      </View>
    </TouchableOpacity>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function JobsScreen() {
  const [jobs, setJobs]         = useState<LocalJob[]>([]);
  const [filter, setFilter]     = useState<Filter>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading]   = useState(true);

  const load = useCallback(async () => {
    try { setJobs(await getJobs(200)); }
    catch { /* stale */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const displayed = filter === 'all' ? jobs : jobs.filter(j => j.status === filter);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>💼 Jobs</Text>
        <View style={styles.headerRight}>
          <Text style={styles.headerCount}>{displayed.length}</Text>
          <Text style={styles.headerCountLabel}> jobs</Text>
        </View>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {FILTERS.map(f => (
          <TouchableOpacity key={f}
            style={[styles.filterChip, filter === f && styles.filterChipActive]}
            onPress={() => setFilter(f)}>
            <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={C.accentMid} /></View>
      ) : displayed.length === 0 ? (
        <View style={styles.center}>
          <View style={styles.emptyIcon}><Ionicons name="briefcase-outline" size={32} color={C.textMuted} /></View>
          <Text style={styles.emptyTitle}>No jobs yet</Text>
          <Text style={styles.emptyText}>Tap Launch on the Dashboard to start</Text>
        </View>
      ) : (
        <FlatList
          data={displayed}
          keyExtractor={item => String(item.id)}
          renderItem={({ item }) => <JobCard job={item} onApplied={load} />}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accentMid} />}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:         { flex: 1, backgroundColor: C.bg },
  header:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                      paddingHorizontal: 20, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:      { fontSize: 18, fontWeight: '800', color: C.text },
  headerRight:      { flexDirection: 'row', alignItems: 'baseline' },
  headerCount:      { fontSize: 18, fontWeight: '800', color: C.accentLight },
  headerCountLabel: { fontSize: 12, color: C.textMuted },
  filterRow:        { paddingHorizontal: 16, paddingVertical: 10, gap: 8 },
  filterChip:       { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 50,
                      backgroundColor: C.card, borderWidth: 1, borderColor: C.border },
  filterChipActive: { backgroundColor: C.accentBg, borderColor: C.accentMid },
  filterText:       { fontSize: 12, color: C.textSub, fontWeight: '500' },
  filterTextActive: { color: C.accentLight, fontWeight: '700' },
  list:             { padding: 16, paddingBottom: 32 },
  center:           { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10 },
  emptyIcon:        { width: 64, height: 64, borderRadius: 20, backgroundColor: C.card,
                      alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  emptyTitle:       { fontSize: 15, fontWeight: '700', color: C.textSub },
  emptyText:        { fontSize: 12, color: C.textMuted, textAlign: 'center', paddingHorizontal: 32 },
  card:             { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                      borderRadius: 18, padding: 14, gap: 12,
                      shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 8, elevation: 2 },
  cardTop:          { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  scoreRing:        { width: 44, height: 44, borderRadius: 12, borderWidth: 2,
                      alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  scoreNum:         { fontSize: 13, fontWeight: '800', lineHeight: 16 },
  scorePct:         { fontSize: 8, color: C.textMuted, lineHeight: 10 },
  cardTitle:        { fontSize: 14, fontWeight: '700', color: C.text, lineHeight: 20 },
  cardCompany:      { fontSize: 11, color: C.textSub },
  badge:            { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 50, flexShrink: 0 },
  badgeText:        { fontSize: 9, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  cardFooter:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  metaChip:         { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText:         { fontSize: 11, color: C.textMuted },
  applyBtn:         { flexDirection: 'row', alignItems: 'center', gap: 6,
                      backgroundColor: C.accent, paddingHorizontal: 14, paddingVertical: 8,
                      borderRadius: 50, shadowColor: C.accent, shadowOpacity: 0.4, shadowRadius: 8, elevation: 3 },
  appliedBadge:     { flexDirection: 'row', alignItems: 'center', gap: 5 },
  applyBtnText:     { fontSize: 12, fontWeight: '700', color: '#fff' },
});
