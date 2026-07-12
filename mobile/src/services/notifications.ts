import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function requestPermissions(): Promise<boolean> {
  const { status: existing } = await Notifications.getPermissionsAsync();
  if (existing === 'granted') return true;
  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}

export async function sendJobsFoundNotification(
  newJobs: number,
  appliedJobs: number,
): Promise<void> {
  try {
    const granted = await requestPermissions();
    if (!granted) return;

    await Notifications.scheduleNotificationAsync({
      content: {
        title: `🤖 Job Bot — ${newJobs} new jobs found`,
        body: appliedJobs > 0
          ? `${appliedJobs} jobs ready to apply. Tap to review.`
          : `Tap to review matching jobs.`,
        sound: true,
        data: { screen: 'Jobs' },
      },
      trigger: null, // immediate
    });
  } catch { /* silent */ }
}

export async function sendCycleNotification(message: string): Promise<void> {
  try {
    const granted = await requestPermissions();
    if (!granted) return;
    await Notifications.scheduleNotificationAsync({
      content: { title: '🤖 Job Bot', body: message, sound: false },
      trigger: null,
    });
  } catch { /* silent */ }
}
