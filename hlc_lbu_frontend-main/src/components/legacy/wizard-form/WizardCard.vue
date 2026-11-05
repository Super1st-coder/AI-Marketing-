<script setup lang="ts">
interface Props {
  paddingY?: "sm" | "lg";
  invisible?: boolean;
}

withDefaults(defineProps<Props>(), { paddingY: "sm", invisible: true });
</script>

<template>
  <div
    class="card tw:rounded-[20px] tw:px-[30px] tw:lg:px-[60px]"
    :class="{
      invisible: invisible,
      'tw:border-2 tw:border-white tw:bg-[rgb(255,255,255,0.35)]': !invisible,
      'tw:py-[30px] tw:lg:py-[60px]': paddingY === 'lg',
      'tw:py-[10px] tw:lg:py-[20px]': paddingY === 'sm',
    }"
  >
    <slot />
  </div>
</template>

<style lang="scss" scoped>
.card {
  box-shadow: 0 16px 20px rgb(61, 41, 34, 0.08);

  &.invisible {
    box-shadow: none;
  }
}
</style>
