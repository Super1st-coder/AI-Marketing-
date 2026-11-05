<script setup lang="ts">
defineProps<{
  name: string;
  objective?: string;
  hasContext: boolean;
}>();
</script>

<template>
  <div class="tw:min-w-0">
    <p
      :title="name"
      class="tw:mb-1 tw:truncate tw:text-sm tw:font-bold"
      style="max-width: 550px"
    >
      {{ name }}
    </p>

    <div class="tw:flex tw:flex-wrap tw:items-center tw:gap-2">
      <Chip
        color="secondary"
        variant="label"
        size="sm"
        leftIcon="tabler:brand-meta"
        class="tw:uppercase"
      />

      <Chip color="secondary" variant="label" size="sm" class="tw:uppercase">
        {{
          $te(`luca-guide.home.campaigns.objectives.${objective}`)
            ? $t(`luca-guide.home.campaigns.objectives.${objective}`)
            : objective
        }}
      </Chip>

      <Chip
        :color="hasContext ? 'info' : 'secondary'"
        variant="label"
        size="sm"
        :leftIcon="hasContext ? 'tabler:file-text' : 'tabler:file-x'"
        class="tw:uppercase"
        :outline="!hasContext"
        :class="{
          'tw:border tw:border-dashed tw:border-gray-400': !hasContext,
        }"
      >
        {{
          $t(
            hasContext
              ? "luca-guide.home.campaigns.with-context"
              : "luca-guide.home.campaigns.without-context",
          )
        }}
      </Chip>
    </div>
  </div>
</template>
