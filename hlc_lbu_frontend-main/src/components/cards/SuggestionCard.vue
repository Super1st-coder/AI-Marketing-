<script lang="ts" setup>
import { type CardBaseProps } from "./base/CardBase.vue";

export interface Props extends CardBaseProps {
  imageSrc?: string;
  icon?: string;
}

const props = defineProps<Props>();

const cardProps = computed(() => {
  // Exclude local props
  const { imageSrc, icon, ...restOfProperties } = props;

  return restOfProperties;
});
</script>

<template>
  <CardBase
    v-bind="cardProps"
    class="tw:flex tw:flex-col tw:items-start tw:p-4"
  >
    <!-- Image -->
    <img v-if="imageSrc" :src="imageSrc" class="tw:mb-3 tw:h-[60px]" />

    <slot name="top" />

    <!-- Icon -->
    <Icon
      v-if="icon"
      :icon="icon"
      class="tw:mb-3 tw:text-xl tw:text-gray-500"
    />

    <!-- Title -->
    <h2 class="tw:mb-2 tw:font-semibold">
      <slot name="title" />
    </h2>

    <!-- Description -->
    <p
      class="tw:grow tw:text-sm tw:text-gray-500"
      :class="{
        'tw:mb-4': $slots.default || $slots.action || $slots.link,
      }"
    >
      <slot name="description" />
    </p>

    <!-- General slot -->
    <slot />

    <!-- General slot for actions -->
    <slot name="action" />

    <!-- Slot dedicated for links (it sets the font size) -->
    <div v-if="$slots.link" class="tw:text-sm">
      <slot name="link" />
    </div>
  </CardBase>
</template>
