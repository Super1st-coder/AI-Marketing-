<script setup lang="ts">
const props = defineProps<{
  fullName: string;
  email?: string;
}>();

const userInitials = computed(() => getUserInitials(props.fullName));
</script>

<template>
  <div class="tw:flex tw:items-center tw:gap-4">
    <AvatarIcon :initials="userInitials" />

    <div>
      <div class="tw:font-medium">{{ fullName }}</div>
      <div class="tw:text-sm tw:text-secondary-text">
        {{ email }}
      </div>
    </div>
  </div>
</template>
