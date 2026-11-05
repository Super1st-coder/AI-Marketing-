<script setup lang="ts">
import type { AdsExperimentSubcategory } from "@/services/funnel-flow/paid-social/AdsExperiment";

defineProps<{
  execution: AdsExperimentSubcategory;
  isSelected: boolean;
}>();
</script>

<template>
  <CardBase
    is="button"
    type="button"
    :color="isSelected ? 'primary' : 'default'"
    hoverColor="primary"
    class="tw:p-4"
  >
    <h3 class="tw:font-bold">
      {{
        $te(
          `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(execution.name)}.name`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(execution.name)}.name`,
            )
          : execution.name
      }}
    </h3>

    <p class="tw:text-sm tw:text-secondary-text">
      {{
        $te(
          `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(execution.name)}.description`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(execution.name)}.description`,
            )
          : execution.description
      }}
    </p>
  </CardBase>
</template>
