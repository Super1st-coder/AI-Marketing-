<script setup lang="ts">
defineProps<{
  title?: string;
  icon?: string;
}>();
</script>

<template>
  <CardBase class="tw:divide-y tw:divide-divider tw:self-start">
    <div v-if="title ?? icon" class="tw:flex tw:items-center tw:gap-3 tw:p-4">
      <Icon
        v-if="icon"
        :icon="icon"
        class="tw:shrink-0 tw:text-2xl tw:text-gray-500"
      />

      <span v-if="title" class="tw:font-semibold tw:text-gray-700">
        {{ title }}
      </span>
    </div>

    <slot />
  </CardBase>
</template>
