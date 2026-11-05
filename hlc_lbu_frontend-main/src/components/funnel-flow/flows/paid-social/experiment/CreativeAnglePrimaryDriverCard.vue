<script setup lang="ts">
import type { AdsExperimentCategory } from "@/services/funnel-flow/paid-social/AdsExperiment";

defineProps<{
  driver: AdsExperimentCategory;
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
          `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(driver.name)}.name`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(driver.name)}.name`,
            )
          : driver.name
      }}
    </h3>

    <p class="tw:text-sm tw:text-secondary-text">
      {{
        $te(
          `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(driver.name)}.description`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(driver.name)}.description`,
            )
          : driver.description
      }}
    </p>
  </CardBase>
</template>
