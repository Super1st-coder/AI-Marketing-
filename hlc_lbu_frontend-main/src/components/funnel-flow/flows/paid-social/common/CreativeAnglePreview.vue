<script setup lang="ts">
import type { AdsExperimentByAdSetData } from "@/services/funnel-flow/paid-social/AdsExperiment";

defineProps<{
  creativeAngle: AdsExperimentByAdSetData;
}>();
</script>

<template>
  <div>
    <!-- Chips -->
    <ChipList class="tw:mb-4">
      <Chip color="primary" variant="label">
        {{
          $t(
            `funnel-flow.paid-social.creative-angle.formats.${creativeAngle.type}.title`,
          )
        }}
      </Chip>

      <Chip color="info" variant="label">
        {{
          $te(
            `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(creativeAngle.subcategory.category.name)}.name`,
          )
            ? $t(
                `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(creativeAngle.subcategory.category.name)}.name`,
              )
            : creativeAngle.subcategory.category.name
        }}
      </Chip>
    </ChipList>

    <!-- Description -->
    <p>
      {{
        $te(
          `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(creativeAngle.subcategory.name)}.description`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(creativeAngle.subcategory.name)}.description`,
            )
          : creativeAngle.subcategory.description
      }}
    </p>
  </div>
</template>
