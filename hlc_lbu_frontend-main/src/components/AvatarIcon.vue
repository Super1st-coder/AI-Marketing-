<script setup lang="ts">
defineProps<{
  initials?: string;
}>();
</script>

<template>
  <div
    class="tw:flex tw:h-[38px] tw:w-[38px] tw:items-center tw:justify-center tw:rounded-full tw:bg-primary tw:text-sm tw:font-bold tw:text-white"
  >
    {{ initials }}
  </div>
</template>
