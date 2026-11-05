<script setup lang="ts">
import { type CardBaseProps } from "./base/CardBase.vue";

interface CardButtonProps extends Omit<
  CardBaseProps,
  "is" | "borderRadius" | "hoverColor"
> {
  icon?: string;
}

const props = defineProps<CardButtonProps>();

const cardProps = computed(() => {
  // Exclude local props
  const { icon, ...restOfProperties } = props;

  return restOfProperties;
});
</script>

<template>
  <CardBase
    is="button"
    borderRadius="md"
    hoverColor="primary"
    class="tw:flex tw:gap-3 tw:p-4"
    v-bind="cardProps"
  >
    <Icon v-if="icon" :icon="icon" class="tw:text-[24px]" />

    <div>
      <h3 class="tw:mb-1 tw:font-bold">
        <slot name="title" />
      </h3>

      <p class="tw:text-sm tw:text-secondary-text">
        <slot name="description" />
      </p>
    </div>

    <slot name="after" />
  </CardBase>
</template>
