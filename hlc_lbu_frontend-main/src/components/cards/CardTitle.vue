<script setup lang="ts">
import { IconCardProps, IconCardVariant } from "./IconCard.vue";

interface Props {
  is?: string | Component;
  icon?: string;
  iconSrc?: string;
  iconVariant?: IconCardVariant;
  iconProps?: IconCardProps;
}

const props = withDefaults(defineProps<Props>(), { is: "h3" });

const hasIcon = computed(
  () => props.icon || props.iconSrc || props.iconProps?.icon,
);
</script>

<template>
  <component
    :is="is"
    class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
    :class="{ 'tw:flex tw:items-center tw:gap-4': hasIcon }"
  >
    <IconCard
      v-if="hasIcon"
      :icon="icon"
      :src="iconSrc"
      :variant="iconVariant"
      size="md"
      v-bind="iconProps"
    />

    <span class="tw:grow">
      <slot />

      <span v-if="$slots.subtitle" class="tw:text-sm tw:font-normal">
        <br />
        <slot name="subtitle" />
      </span>
    </span>

    <slot name="after" />
  </component>
</template>
