import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet } from 'react-native';

import DashboardScreen from './src/screens/DashboardScreen';
import JobsScreen      from './src/screens/JobsScreen';
import LogsScreen      from './src/screens/LogsScreen';
import SettingsScreen  from './src/screens/SettingsScreen';
import { C }           from './src/theme';

const Tab = createBottomTabNavigator();

type IoniconsName = React.ComponentProps<typeof Ionicons>['name'];

const TAB_ICONS: Record<string, [IoniconsName, IoniconsName]> = {
  Dashboard: ['grid',       'grid-outline'],
  Jobs:      ['briefcase',  'briefcase-outline'],
  Logs:      ['terminal',   'terminal-outline'],
  Settings:  ['settings',   'settings-outline'],
};

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarStyle: styles.tabBar,
          tabBarActiveTintColor:   C.accent,
          tabBarInactiveTintColor: C.textMuted,
          tabBarIcon: ({ focused, color, size }) => {
            const [activeIcon, inactiveIcon] = TAB_ICONS[route.name] ?? ['ellipse', 'ellipse-outline'];
            return (
              <Ionicons
                name={focused ? activeIcon : inactiveIcon}
                size={size}
                color={color}
              />
            );
          },
          tabBarLabelStyle: styles.tabLabel,
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
    backgroundColor:  C.card,
    borderTopColor:   C.border,
    borderTopWidth:   1,
    paddingBottom:    4,
    height:           58,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '500',
  },
});
