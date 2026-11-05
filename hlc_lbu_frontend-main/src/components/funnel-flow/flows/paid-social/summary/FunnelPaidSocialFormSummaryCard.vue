<script setup lang="ts">
defineProps<{ imgSrc?: string | null }>();
</script>

<template>
  <CardBase class="tw:flex tw:cursor-pointer tw:flex-col tw:gap-3.5 tw:p-5">
    <h3 class="tw:text-sm tw:font-extrabold">
      <slot name="title" />
    </h3>

    <Separator />

    <img v-if="imgSrc" :src="imgSrc" />

    <p class="tw:line-clamp-4 tw:text-xs tw:text-secondary">
      <slot name="description" />
    </p>
  </CardBase>
</template>
