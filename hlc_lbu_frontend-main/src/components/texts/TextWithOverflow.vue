<script setup lang="ts">
interface Props {
  is?: string | Component;
  disableClamp?: boolean;
  variant?: "plusMinus" | "chevron";
}

const props = withDefaults(defineProps<Props>(), {
  is: "p",
  disableClamp: false,
  variant: "plusMinus",
});

const textRef = ref<HTMLParagraphElement | null>(null);
const isOverflowing = ref(false);
const isExpanded = ref(false);

const checkOverflow = () => {
  if (!textRef.value || isExpanded.value || props.disableClamp) return;
  isOverflowing.value = textRef.value.scrollHeight > textRef.value.offsetHeight;
};

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

// Watch for window size changes
const { width, height } = useWindowSize();
watch([width, height], () => {
  checkOverflow();
});

// Watch clamp prop to reset state when disabled
watch(
  () => props.disableClamp,
  (disableClamp) => {
    if (disableClamp) {
      isOverflowing.value = false;
      isExpanded.value = false;
    } else {
      checkOverflow();
    }
  },
);

// Observe element size changes
useResizeObserver(textRef, () => {
  checkOverflow();
});

onMounted(() => {
  checkOverflow();
});

onUpdated(() => {
  checkOverflow();
});
</script>

<template>
  <component :is="is">
    <span
      ref="textRef"
      class="tw:mb-4"
      :class="
        props.disableClamp || isExpanded
          ? 'tw:line-clamp-none'
          : 'tw:line-clamp-2'
      "
    >
      <slot />
    </span>

    <!-- See more/less button -->
    <Button
      v-if="$slots.default && !props.disableClamp && isOverflowing"
      @click.stop="toggleExpand"
      type="button"
      variant="text"
      color="primary"
      :leftIcon="
        variant === 'plusMinus'
          ? isExpanded
            ? 'tabler:minus'
            : 'tabler:plus'
          : undefined
      "
      :icon="
        variant === 'chevron'
          ? isExpanded
            ? 'tabler:chevron-up'
            : 'tabler:chevron-down'
          : undefined
      "
      size="sm"
      class="tw:p-0!"
    >
      <slot name="buttonContent" v-bind="{ isExpanded }">
        <span>{{
          isExpanded ? $t("global.see-less") : $t("global.see-more")
        }}</span>
      </slot>
    </Button>
  </component>
</template>
