import * as BackgroundFetch from 'expo-background-fetch';
import * as TaskManager from 'expo-task-manager';
import { runBotCycle } from './bot';
import { loadSettings } from './settings';

export const TASK_NAME = 'JOB_BOT_CYCLE';

// Register the task definition (call at app top-level, outside any component)
export function defineTask(): void {
  if (TaskManager.isTaskDefined(TASK_NAME)) return;

  TaskManager.defineTask(TASK_NAME, async () => {
    try {
      await runBotCycle();
      return BackgroundFetch.BackgroundFetchResult.NewData;
    } catch {
      return BackgroundFetch.BackgroundFetchResult.Failed;
    }
  });
}

export async function registerBackgroundFetch(): Promise<void> {
  const settings = await loadSettings();
  const intervalSeconds = Math.max(15 * 60, settings.intervalMinutes * 60);

  const status = await BackgroundFetch.getStatusAsync();
  if (
    status === BackgroundFetch.BackgroundFetchStatus.Restricted ||
    status === BackgroundFetch.BackgroundFetchStatus.Denied
  ) {
    console.warn('[scheduler] Background fetch is restricted/denied');
    return;
  }

  await BackgroundFetch.registerTaskAsync(TASK_NAME, {
    minimumInterval: intervalSeconds,
    stopOnTerminate: false,
    startOnBoot:     true,
  });
}

export async function unregisterBackgroundFetch(): Promise<void> {
  const registered = await TaskManager.isTaskRegisteredAsync(TASK_NAME);
  if (registered) await BackgroundFetch.unregisterTaskAsync(TASK_NAME);
}

export async function isScheduled(): Promise<boolean> {
  return TaskManager.isTaskRegisteredAsync(TASK_NAME);
}
