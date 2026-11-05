import { defineStore } from "pinia";

export type NotificationType = "success" | "error" | "warning" | "info";

export interface NotificationItem {
  id: number;
  type: NotificationType;
  title?: string;
  description?: string;
}

export interface NotificationDisplayOptions {
  type: NotificationType;
  title?: string;
  description?: string;
  durationMs?: number | null;
}

export type NotificationUpdateOptions = Partial<
  Pick<NotificationItem, "type" | "title" | "description">
>;

export const DEFAULT_NOTIFICATION_TIME_MS = 5000;

export const useNotificationStore = defineStore("NotificationStore", () => {
  const queue = ref<NotificationItem[]>([]);
  const timers = new Map<number, ReturnType<typeof setTimeout>>();

  const clearTimer = (id: number) => {
    const handle = timers.get(id);

    if (handle !== undefined) {
      clearTimeout(handle);
      timers.delete(id);
    }
  };

  const dismiss = (id: number) => {
    clearTimer(id);
    queue.value = queue.value.filter((item) => item.id !== id);
  };

  const display = (options: NotificationDisplayOptions) => {
    // Generate id
    const id = new Date().getTime();

    // Push notification to queu
    queue.value.push({
      id,
      type: options.type,
      title: options.title,
      description: options.description,
    });

    // Start timeout
    if (options.durationMs !== null) {
      const duration = options.durationMs ?? DEFAULT_NOTIFICATION_TIME_MS;
      const timeoutId = setTimeout(() => {
        dismiss(id);
      }, duration);
      timers.set(id, timeoutId);
    }

    return id;
  };

  const update = (id: number, options: NotificationUpdateOptions): boolean => {
    const index = queue.value.findIndex((item) => item.id === id);
    if (index === -1) return false;

    queue.value[index] = {
      ...queue.value[index],
      ...options,
    };

    return true;
  };

  return {
    queue: readonly(queue),
    display,
    update,
    dismiss,
  };
});
