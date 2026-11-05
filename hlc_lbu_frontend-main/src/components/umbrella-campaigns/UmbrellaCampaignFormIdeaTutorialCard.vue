<script setup lang="ts">
defineProps<{ imageSrc: string }>();
</script>

<template>
  <CardBase class="tw:flex tw:flex-col tw:items-center tw:p-8 tw:text-center">
    <img :src="imageSrc" class="tw:mb-8 tw:h-[120px]" />

    <h2 class="tw:mb-4 tw:text-lg tw:font-extrabold">
      <slot name="title" />
    </h2>

    <p>
      <slot />
    </p>
  </CardBase>
</template>
