<script setup lang="ts">
const props = defineProps<{
  title: string;
  description: string;
}>();
</script>

<template>
  <h3 class="tw:mb-6 tw:text-xl tw:font-bold">
    {{ props.title }}
  </h3>
  <div class="tw:flex tw:justify-center">
    <Icon
      icon="tabler:loader-2"
      class="tw:mb-3 tw:animate-spin tw:text-[50px] tw:text-primary"
    />
  </div>
  <p class="tw:mt-6">
    {{ props.description }}
  </p>
</template>

<style></style>
