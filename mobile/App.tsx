import React from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';

import DashboardScreen from './src/screens/DashboardScreen';
import JobsScreen      from './src/screens/JobsScreen';
import LogsScreen      from './src/screens/LogsScreen';
import SettingsScreen  from './src/screens/SettingsScreen';
import { C }           from './src/theme';
import { defineTask }  from './src/services/scheduler';

const Tab = createBottomTabNavigator();

// Register the background task definition at module level (required by expo-task-manager)
defineTask();

const NAV_THEME = { ...DefaultTheme, colors: { ...DefaultTheme.colors, background: C.bg } };

type IoniconsName = React.ComponentProps<typeof Ionicons>['name'];

const TAB_ICONS: Record<string, [IoniconsName, IoniconsName]> = {
  Dashboard: ['grid',       'grid-outline'],
  Jobs:      ['briefcase',  'briefcase-outline'],
  Logs:      ['terminal',   'terminal-outline'],
  Settings:  ['settings',   'settings-outline'],
};

export default function App() {
  return (
    <NavigationContainer theme={NAV_THEME}>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarStyle: styles.tabBar,
          tabBarActiveTintColor:   C.accentLight,
          tabBarInactiveTintColor: C.textMuted,
          tabBarIcon: ({ focused, color, size }) => {
            const [activeIcon, inactiveIcon] = TAB_ICONS[route.name] ?? ['ellipse', 'ellipse-outline'];
            return (
              <View style={[styles.tabIconWrap, focused && styles.tabIconActive]}>
                <Ionicons name={focused ? activeIcon : inactiveIcon} size={20} color={color} />
              </View>
            );
          },
          tabBarLabelStyle: styles.tabLabel,
          tabBarItemStyle:  styles.tabItem,
        })}
      >
        <Tab.Screen name="Dashboard" component={DashboardScreen} />
        <Tab.Screen name="Jobs"      component={JobsScreen} />
        <Tab.Screen name="Logs"      component={LogsScreen} />
        <Tab.Screen name="Settings"  component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: C.card,
    borderTopColor:  C.border,
    borderTopWidth:  1,
    paddingTop:      4,
    height:          64,
    elevation:       16,
    shadowColor:     C.accent,
    shadowOpacity:   0.2,
    shadowRadius:    16,
  },
  tabItem:       { paddingTop: 4 },
  tabLabel:      { fontSize: 10, fontWeight: '600', marginTop: 2 },
  tabIconWrap:   { width: 36, height: 28, alignItems: 'center', justifyContent: 'center', borderRadius: 10 },
  tabIconActive: { backgroundColor: C.accentBg },
});
