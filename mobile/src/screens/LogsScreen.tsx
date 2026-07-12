import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getLogs, clearLogs as dbClearLogs } from '../services/database';
import { C, logColor } from '../theme';

interface LogEntry { message: string; level: string; timestamp: string; }

export default function LogsScreen() {
  const [logs, setLogs]       = useState<LogEntry[]>([]);
  const [live, setLive]       = useState(true);
  const [loading, setLoading] = useState(true);
  const scrollRef             = useRef<ScrollView>(null);
  const countRef              = useRef(0);

  const load = useCallback(async (replace = false) => {
    try {
      const data = await getLogs(200);
      if (replace) {
        setLogs(data.reverse());
      } else if (data.length !== countRef.current) {
        setLogs(data.reverse());
        countRef.current = data.length;
        scrollRef.current?.scrollToEnd({ animated: true });
      }
    } catch { /* keep stale */ }
    finally { setLoading(false); }
  }, []);

  // Initial load
  useEffect(() => { load(true); }, [load]);

  // Polling while live is on
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => load(false), 2000);
    return () => clearInterval(id);
  }, [live, load]);

  const handleClear = async () => { await dbClearLogs(); setLogs([]); };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📋 Live Logs</Text>
        <View style={styles.headerRight}>
          <Text style={styles.liveLabel}>{live ? 'Live' : 'Paused'}</Text>
          <Switch
            value={live}
            onValueChange={setLive}
            trackColor={{ false: C.border, true: C.accent }}
            thumbColor="#fff"
          />
          <TouchableOpacity onPress={handleClear} style={styles.clearBtn}>
            <Ionicons name="trash-outline" size={18} color={C.textMuted} />
          </TouchableOpacity>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={C.accent} />
        </View>
      ) : logs.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="terminal-outline" size={48} color={C.border} />
          <Text style={styles.emptyText}>No logs yet</Text>
        </View>
      ) : (
        <ScrollView
          ref={scrollRef}
          style={styles.logScroll}
          contentContainerStyle={styles.logContent}
          onContentSizeChange={() => live && scrollRef.current?.scrollToEnd({ animated: false })}
        >
          {logs.map((entry, i) => {
            const msg       = entry.message || '';
            const ts        = entry.timestamp?.slice(11, 19) ?? '';
            const color     = logColor(msg);
            const isError   = msg.includes('ERROR');
            const isWarning = msg.includes('WARNING');
            return (
              <View
                key={i}
                style={[
                  styles.logLine,
                  isError   && styles.logLineError,
                  isWarning && styles.logLineWarn,
                ]}
              >
                <Text style={[styles.logTime, { color: C.textMuted }]}>{ts}</Text>
                <Text style={[styles.logMsg, { color }]} selectable>
                  {msg}
                </Text>
              </View>
            );
          })}
        </ScrollView>
      )}

      {/* Live indicator pill */}
      {live && (
        <View style={styles.livePill}>
          <View style={styles.liveDot} />
          <Text style={styles.livePillText}>Live</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea:      { flex: 1, backgroundColor: C.bg },
  header:        { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                   paddingHorizontal: 16, paddingVertical: 12,
                   borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:   { fontSize: 18, fontWeight: '700', color: C.text },
  headerRight:   { flexDirection: 'row', alignItems: 'center', gap: 10 },
  liveLabel:     { fontSize: 12, color: C.textMuted },
  clearBtn:      { padding: 4 },
  center:        { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  emptyText:     { color: C.textMuted, fontSize: 14 },
  logScroll:     { flex: 1 },
  logContent:    { padding: 12, gap: 2 },
  logLine:       { flexDirection: 'row', gap: 8, paddingVertical: 2,
                   borderRadius: 4, paddingHorizontal: 4 },
  logLineError:  { backgroundColor: '#7f1d1d18' },
  logLineWarn:   { backgroundColor: '#7c2d1218' },
  logTime:       { fontFamily: 'monospace', fontSize: 10, paddingTop: 2, width: 60 },
  logMsg:        { flex: 1, fontFamily: 'monospace', fontSize: 10, lineHeight: 16 },
  livePill:      { position: 'absolute', bottom: 16, right: 16,
                   flexDirection: 'row', alignItems: 'center', gap: 6,
                   backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
                   paddingHorizontal: 12, paddingVertical: 6, borderRadius: 50,
                   shadowColor: '#000', shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  liveDot:       { width: 7, height: 7, borderRadius: 4, backgroundColor: C.green },
  livePillText:  { fontSize: 11, color: C.green, fontWeight: '700' },
});
