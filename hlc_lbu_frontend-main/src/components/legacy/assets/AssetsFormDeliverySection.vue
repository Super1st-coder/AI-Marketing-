<script setup lang="ts">
import { IconCardVariant } from "@/components/cards/IconCard.vue";

defineProps<{
  icon: string;
  iconVariant: IconCardVariant;
  imageSrc?: string | null;
}>();
</script>

<template>
  <div class="tw:grid tw:gap-8 tw:lg:grid-cols-2">
    <div class="tw:flex tw:flex-col tw:gap-8">
      <CardTitle :icon="icon" :iconVariant="iconVariant">
        <slot name="title" />
      </CardTitle>

      <slot />
    </div>

    <div
      class="tw:flex tw:aspect-square tw:items-center tw:justify-center tw:overflow-hidden tw:rounded-[5px] tw:bg-[#DFDAEA]"
    >
      <img
        v-if="imageSrc"
        :src="imageSrc"
        class="tw:h-full tw:w-full tw:bg-contain"
      />
    </div>
  </div>
</template>
