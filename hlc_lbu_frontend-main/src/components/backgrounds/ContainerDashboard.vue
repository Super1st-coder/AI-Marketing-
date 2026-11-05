<script lang="ts" setup>
import type { ContainerProps } from "@/components/backgrounds/Container.vue";

const props = withDefaults(defineProps<ContainerProps>(), { maxWidth: 1160 });
</script>

<template>
  <Container
    v-bind="props"
    class="tw:flex tw:h-full tw:flex-col tw:gap-10 tw:py-4 tw:md:py-6"
  >
    <slot />
  </Container>
</template>
