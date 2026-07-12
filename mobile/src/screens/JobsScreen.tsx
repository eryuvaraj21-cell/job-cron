import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, Linking, ScrollView, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { fetchJobs, Job } from '../api';
import { C, statusColor, statusBg, fmtDate } from '../theme';

const FILTERS = ['all', 'applied', 'manual_needed', 'failed', 'skipped'] as const;
type Filter = typeof FILTERS[number];

// ── Job card ───────────────────────────────────────────────────────────────────

function JobCard({ job }: { job: Job }) {
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
  const [jobs, setJobs]         = useState<Job[]>([]);
  const [filter, setFilter]     = useState<Filter>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading]   = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchJobs(150);
      setJobs(data);
    } catch { /* keep showing stale data */ }
    finally   { setLoading(false); }
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
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>💼 Jobs</Text>
        <Text style={styles.headerCount}>{displayed.length} shown</Text>
      </View>

      {/* Filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
      >
        {FILTERS.map(f => (
          <TouchableOpacity
            key={f}
            style={[styles.filterChip, filter === f && styles.filterChipActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={C.accent} />
        </View>
      ) : displayed.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="briefcase-outline" size={48} color={C.border} />
          <Text style={styles.emptyText}>No jobs found</Text>
        </View>
      ) : (
        <FlatList
          data={displayed}
          keyExtractor={item => String(item.id)}
          renderItem={({ item }) => <JobCard job={item} />}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
          ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:         { flex: 1, backgroundColor: C.bg },
  header:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                      paddingHorizontal: 16, paddingVertical: 12,
                      borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:      { fontSize: 18, fontWeight: '700', color: C.text },
  headerCount:      { fontSize: 12, color: C.textMuted },
  filterRow:        { paddingHorizontal: 14, paddingVertical: 10, gap: 8 },
  filterChip:       { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 50,
                      backgroundColor: C.card, borderWidth: 1, borderColor: C.border },
  filterChipActive: { backgroundColor: C.accent, borderColor: C.accent },
  filterText:       { fontSize: 12, color: C.textSub, fontWeight: '500' },
  filterTextActive: { color: '#fff', fontWeight: '700' },
  list:             { padding: 14, paddingBottom: 32 },
  center:           { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  emptyText:        { color: C.textMuted, fontSize: 14 },
  card:             { backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                      borderRadius: 16, padding: 14 },
  cardTop:          { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 6 },
  cardTitle:        { flex: 1, fontSize: 14, fontWeight: '600', color: C.blue, lineHeight: 20 },
  badge:            { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 50 },
  badgeText:        { fontSize: 10, fontWeight: '700' },
  cardCompany:      { fontSize: 12, color: C.textSub, marginBottom: 10 },
  cardMeta:         { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  metaChip:         { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText:         { fontSize: 11, color: C.textMuted },
});
