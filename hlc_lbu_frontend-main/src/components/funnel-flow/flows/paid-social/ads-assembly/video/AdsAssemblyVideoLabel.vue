<script setup lang="ts">
defineProps<{ icon: string }>();
</script>

<template>
  <div class="tw:flex tw:items-center tw:gap-3">
    <Icon :icon="icon" class="tw:shrink-0 tw:text-[20px] tw:text-primary" />

    <div>
      <h2 class="tw:text-base tw:font-bold tw:text-primary-text">
        <slot name="title" />
      </h2>

      <p v-if="$slots.description" class="tw:text-xs tw:text-secondary-text">
        <slot name="description" />
      </p>
    </div>
  </div>
</template>
