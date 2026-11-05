<script setup lang="ts">
interface Props {
  selected?: boolean;
  clamp?: boolean;
  // Shows the card as plain content, without the button behavior
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
});
</script>

<template>
  <CardBase
    :is="readonly ? 'div' : 'button'"
    :outlineColor="selected ? 'primary' : 'default'"
    :hoverColor="readonly ? undefined : 'primary'"
    :shadow="false"
    class="tw:px-4 tw:py-5"
    :borderWidth="2"
  >
    <!-- Title -->
    <h3
      v-if="$slots.title"
      class="tw:text-sm tw:font-semibold"
      :class="{
        'tw:mb-2': $slots.default,
        'tw:flex tw:items-center tw:justify-between tw:gap-2':
          $slots.afterTitle,
      }"
    >
      <slot name="title" />

      <slot name="afterTitle" />
    </h3>

    <!-- Text -->
    <TextWithOverflow
      v-if="$slots.default"
      :disableClamp="!props.clamp"
      class="tw:text-sm tw:text-secondary-text"
    >
      <slot />
    </TextWithOverflow>
  </CardBase>
</template>
