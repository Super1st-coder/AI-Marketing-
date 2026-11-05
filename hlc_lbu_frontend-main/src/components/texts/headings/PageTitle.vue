<script setup lang="ts">
interface Props {
  is?: string | Component;
  helpButton?: boolean;
  helpVideoUrl?: string;
  size?: "lg" | "md";
}

withDefaults(defineProps<Props>(), { is: "h1", size: "md" });
</script>

<template>
  <div
    :class="{
      'tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:items-center':
        $slots.after || $slots.actions,
    }"
  >
    <div :class="{ 'tw:grow': $slots.after }">
      <!-- Title -->
      <div class="tw:flex tw:items-start tw:gap-5">
        <component
          :is="is"
          class="tw:font-public-sans tw:leading-tight tw:font-bold tw:wrap-anywhere tw:text-primary-text"
          :class="{
            'tw:text-2xl tw:lg:text-3xl': size === 'md',
            'tw:text-3xl tw:lg:text-4xl': size === 'lg',
          }"
        >
          <slot />
        </component>

        <ButtonVideoHelp v-if="helpButton" :src="helpVideoUrl">
          <slot />
        </ButtonVideoHelp>
      </div>

      <!-- Description -->
      <template v-if="$slots.description">
        <p
          class="tw:mt-2 tw:text-sm tw:whitespace-pre-line tw:text-secondary-text"
        >
          <slot name="description" />
        </p>
      </template>
    </div>

    <div
      v-if="$slots.actions"
      class="tw:flex tw:items-start tw:gap-2 tw:lg:whitespace-nowrap"
    >
      <slot name="actions" />
    </div>

    <div v-if="$slots.after">
      <slot name="after" />
    </div>
  </div>
</template>
