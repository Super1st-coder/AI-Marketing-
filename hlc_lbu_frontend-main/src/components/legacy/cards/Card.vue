<script lang="ts" setup>
interface Props {
  padding?: "none" | "sm" | "md" | "lg";
  variant?: "normal" | "success" | "primary";
  expandable?: boolean;
}

const isExpanded = defineModel<boolean>("expanded");

withDefaults(defineProps<Props>(), { padding: "md", variant: "normal" });
</script>

<template>
  <div
    class="tw:shadow-xl"
    :class="{
      'tw:rounded-[20px] tw:p-5': padding === 'sm',
      'tw:rounded-md tw:p-9 tw:lg:p-12': padding === 'md',
      'tw:rounded-[20px] tw:px-7 tw:py-5 tw:lg:px-12 tw:lg:py-10':
        padding === 'lg',
      'tw:border-transparent tw:bg-white': variant === 'normal',
      'tw:border-success tw:bg-success/8': variant === 'success',
      'tw:border-primary tw:bg-primary/8': variant === 'primary',
    }"
  >
    <slot />

    <button
      v-if="expandable"
      class="tw:mt-5 tw:flex tw:w-full tw:justify-center"
      @click="isExpanded = !isExpanded"
      type="button"
    >
      <Icon
        :icon="isExpanded ? 'tabler-chevron-up' : 'tabler-chevron-down'"
        class="tw:text-2xl"
      />
    </button>
  </div>
</template>
