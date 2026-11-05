<script setup lang="ts">
import type { ChipProps } from "@/components/chips/Chip.vue";
import { CLASSIFICATION_THRESHOLDS } from "@/constants/guide/classification-thresholds";

const props = withDefaults(
  defineProps<{
    state: string;
    size?: ChipProps["size"];
  }>(),
  {
    size: "sm",
  },
);

const config = computed(() =>
  CLASSIFICATION_THRESHOLDS.find((entry) => entry.key === props.state),
);

const { te } = useI18n();

const statusTranslationKey = computed(
  () =>
    `luca-guide.onboarding.classification-thresholds.statuses.${props.state}`,
);
</script>

<template>
  <Chip
    v-if="config"
    :color="config.color"
    variant="label"
    :size="size"
    :leftIcon="config.icon"
    class="tw:uppercase"
  >
    {{ te(statusTranslationKey) ? $t(statusTranslationKey) : state }}
  </Chip>

  <Chip
    v-else
    variant="label"
    color="secondary"
    :size="size"
    class="tw:uppercase"
  >
    {{ te(statusTranslationKey) ? $t(statusTranslationKey) : state }}
  </Chip>
</template>
