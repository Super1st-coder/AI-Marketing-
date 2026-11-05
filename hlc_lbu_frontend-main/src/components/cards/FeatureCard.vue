<script setup lang="ts">
import { IconCardVariant } from "./IconCard.vue";

interface Props {
  src?: string;
  icon?: string;
  color?: string;
  cardClass?: string;
  variant?: IconCardVariant;
}

defineProps<Props>();
</script>

<template>
  <div class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:text-center">
    <IconCard
      size="lg"
      :src="src"
      :icon="icon"
      :class="cardClass"
      :style="{ backgroundColor: color }"
      :variant="variant"
    />

    <h2 class="tw:text-xl tw:font-extrabold">
      <slot />
    </h2>

    <p v-if="$slots.paragraph" class="tw:max-w-80 tw:text-primary-text/60">
      <slot name="paragraph" />
    </p>
  </div>
</template>
