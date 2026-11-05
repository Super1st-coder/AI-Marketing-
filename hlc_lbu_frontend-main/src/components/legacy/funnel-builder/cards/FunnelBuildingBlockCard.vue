<script lang="ts" setup>
import { RouteLocationRaw } from "vue-router";

export type FunnelBuildingBlockStatus = {
  blockCount: number;
  blocksCovered: number;
};

interface Props {
  icon: string;
  to?: RouteLocationRaw;
  status?: FunnelBuildingBlockStatus;
}

const props = defineProps<Props>();

const isReady = computed(
  () => (props.status?.blocksCovered ?? 0) >= (props.status?.blockCount ?? 1),
);
</script>

<template>
  <Card padding="sm" class="tw:flex tw:flex-col tw:gap-4 tw:md:flex-row">
    <div class="tw:flex tw:grow tw:flex-col tw:gap-3">
      <CardTitle :icon="icon" iconVariant="primary">
        <slot name="title" />
      </CardTitle>

      <CardParagraph class="tw:text-[13px] tw:font-medium">
        <slot name="description" />
      </CardParagraph>

      <div class="tw:flex tw:items-end tw:justify-between">
        <p
          class="tw:rounded-[6px] tw:px-3 tw:py-2 tw:text-[13px]"
          :class="{
            'tw:bg-secondary/15 tw:text-secondary/90': !isReady,
            'tw:bg-success-light tw:text-success': isReady,
          }"
        >
          Building blocks covered: {{ status?.blocksCovered }}/{{
            status?.blockCount
          }}
        </p>
      </div>
    </div>

    <div class="tw:flex tw:shrink-0 tw:flex-col tw:items-end tw:gap-3">
      <Button
        icon="tabler-arrow-right"
        size="md"
        :to="to"
        :variant="isReady ? 'outlined' : 'solid'"
      >
        {{ isReady ? "REVIEW" : "BUILD" }}
      </Button>

      <slot name="options" />
    </div>
  </Card>
</template>
