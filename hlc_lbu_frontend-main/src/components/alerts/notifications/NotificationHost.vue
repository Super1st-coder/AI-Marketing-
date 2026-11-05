<script setup lang="ts">
const TOP_NAV_OFFSET_PX = 66 + 24;

const notificationStore = useNotificationStore();
</script>

<template>
  <Teleport to="#notifications">
    <div
      class="tw:pointer-events-none tw:fixed tw:right-3 tw:z-20000 tw:w-[min(100vw-32px,400px)] tw:md:right-6"
      :style="{ top: `${TOP_NAV_OFFSET_PX}px` }"
      aria-live="polite"
    >
      <TransitionGroup
        name="notification-toast"
        tag="div"
        class="tw:relative tw:flex tw:w-full tw:flex-col tw:gap-3"
      >
        <div
          v-for="item in notificationStore.queue"
          :key="item.id"
          class="tw:pointer-events-auto"
        >
          <NotificationToast :notification="item" />
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
/* Vertical FLIP when siblings shift after dismiss (Vue TransitionGroup) */
.notification-toast-move {
  transition: transform 0.38s cubic-bezier(0.22, 1, 0.36, 1);
}

.notification-toast-enter-active,
.notification-toast-leave-active {
  transition:
    transform 0.38s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.32s ease;
}

/* New toasts are appended at the bottom — enter from below */
.notification-toast-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.notification-toast-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/*
 * Take leaving nodes out of flex flow so remaining items animate upward
 * via .notification-toast-move instead of jumping.
 */
.notification-toast-leave-active {
  position: absolute;
  right: 0;
  width: 100%;
}
</style>
