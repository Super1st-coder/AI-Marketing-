<script setup lang="ts">
import type { CardBaseColor } from "@/components/cards/base/CardBase.vue";
import type { NotificationItem } from "@/stores/NotificationStore";

const props = defineProps<{
  notification: NotificationItem;
}>();

const notificationStore = useNotificationStore();

const cardColor = computed<CardBaseColor>(() => {
  switch (props.notification.type) {
    case "success":
      return "success";
    case "error":
      return "error";
    case "warning":
      return "warning";
    case "info":
      return "info";
    default:
      return "default";
  }
});

const statusIcon = computed(() => {
  switch (props.notification.type) {
    case "success":
      return "tabler:circle-check-filled";
    case "error":
      return "tabler:alert-circle-filled";
    case "warning":
      return "tabler:alert-circle-filled";
    case "info":
      return "tabler:info-circle-filled";
    default:
      return "tabler:info-circle-filled";
  }
});

const statusIconWrapClass = computed(() => {
  switch (props.notification.type) {
    case "success":
      return "tw:text-success-500";
    case "error":
      return "tw:text-error-500";
    case "warning":
      return "tw:text-warning-500";
    case "info":
      return "tw:text-blue-500";
    default:
      return "tw:text-gray-500";
  }
});

const textClass = computed(() => {
  switch (props.notification.type) {
    case "success":
      return "tw:text-success-800";
    case "error":
      return "tw:text-error-800";
    case "warning":
      return "tw:text-warning-800";
    case "info":
      return "tw:text-blue-800";
    default:
      return "tw:text-gray-800";
  }
});
</script>

<template>
  <CardBase
    :color="cardColor"
    :outlineColor="cardColor"
    :shadow="false"
    border-radius="md"
    class="tw:flex tw:w-full tw:max-w-[400px] tw:items-start tw:overflow-hidden tw:p-3"
  >
    <Icon
      :icon="statusIcon"
      class="tw:mr-2 tw:shrink-0 tw:text-[24px]"
      :class="statusIconWrapClass"
    />

    <div class="tw:mr-4 tw:grow">
      <p v-if="notification.title" class="tw:font-bold" :class="textClass">
        {{ notification.title }}
      </p>

      <p
        v-if="notification.description"
        class="tw:text-sm tw:font-medium"
        :class="textClass"
      >
        {{ notification.description }}
      </p>
    </div>

    <button
      type="button"
      :class="textClass"
      :aria-label="$t('global.close')"
      @click="notificationStore.dismiss(notification.id)"
    >
      <Icon icon="tabler:x" class="tw:text-2xl" />
    </button>
  </CardBase>
</template>
