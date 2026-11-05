<script lang="ts" setup>
import CardBase from "@/components/cards/base/CardBase.vue";

interface Props {
  type: "secondary" | "error" | "warning" | "success" | "info";
  autoScroll?: boolean;
  /** When true, body content can be collapsed and a chevron toggle is shown. */
  expandable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  expandable: false,
});

/** Optional expanded state. Only used when `expandable` is true. Defaults to expanded. */
const isExpanded = defineModel<boolean>({ default: true });

const icon = computed(() =>
  props.type === "error"
    ? "tabler:alert-circle"
    : props.type === "warning"
      ? "tabler:alert-triangle"
      : props.type === "secondary"
        ? "tabler:exclamation-mark"
        : props.type === "success"
          ? "tabler:circle-check-filled"
          : "tabler:bulb",
);

const cardBaseRef = ref<InstanceType<typeof CardBase>>();
const element = computed(() => cardBaseRef.value?.element);

const scroll = async () => {
  if (element.value) {
    await scrollToFieldElement(element.value);
  }
};

const isSubmitting = useIsSubmitting();
onMounted(() => {
  if (props.autoScroll) {
    scroll();
  }
});

watch(isSubmitting, (isSubmitting) => {
  if (!isSubmitting && props.autoScroll) {
    scroll();
  }
});

function toggleExpanded() {
  isExpanded.value = !isExpanded.value;
}

defineExpose({
  scroll,
  element,
});
</script>

<template>
  <CardBase
    ref="cardBaseRef"
    borderRadius="sm"
    class="tw:flex tw:flex-col tw:items-start tw:gap-2 tw:p-4 tw:text-sm tw:md:flex-row"
    :color="props.type"
    :outlineColor="props.type"
  >
    <div class="tw:flex tw:grow tw:gap-2">
      <Icon
        :icon="icon"
        class="tw:shrink-0 tw:text-2xl"
        :class="{
          'tw:text-success': type === 'success',
          'tw:text-error': type === 'error',
          'tw:text-warning': type === 'warning',
          'tw:text-secondary': type === 'secondary',
          'tw:text-info': type === 'info',
        }"
      />

      <div
        class="tw:text-left tw:font-medium"
        :class="{
          'tw:text-success-800': type === 'success',
          'tw:text-error-900': type === 'error',
          'tw:text-warning-900': type === 'warning',
          'tw:text-primary-text': type === 'secondary',
          'tw:text-blue-900': type === 'info',
        }"
      >
        <h4 v-if="$slots.title" class="tw:text-sm tw:font-bold">
          <slot name="title" />
        </h4>

        <div v-show="!expandable || isExpanded">
          <p v-if="$slots.default">
            <slot />
          </p>

          <slot v-if="$slots.custom" name="custom" />
        </div>
      </div>
    </div>

    <div
      v-if="expandable || $slots.actions"
      class="tw:inline-flex tw:items-center tw:gap-1"
      :class="{
        'tw:self-center': !expandable,
        'tw:self-start': expandable,
      }"
    >
      <slot name="actions" />

      <Button
        v-if="expandable"
        type="button"
        variant="text"
        color="secondary"
        size="xs"
        square
        :shadow="false"
        :icon="isExpanded ? 'tabler:chevron-up' : 'tabler:chevron-down'"
        @click="toggleExpanded"
      />
    </div>
  </CardBase>
</template>
