<script setup lang="ts">
import { AdsExperimentByAdSetData } from "@/services/funnel-flow/paid-social/AdsExperiment";

const props = defineProps<{
  creativeAngle: AdsExperimentByAdSetData;
}>();

const isModalOpen = ref(false);

const { t, te } = useI18n();

const subcategoryName = computed(() => {
  const subcategory = props.creativeAngle?.subcategory;
  if (!subcategory) return "-";

  const key = `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(subcategory.name)}.name`;
  return te(key) ? t(key) : subcategory.name;
});
</script>

<template>
  <Button
    variant="outlined"
    color="secondary"
    size="xs"
    @click="isModalOpen = true"
    :shadow="false"
    :uppercase="false"
  >
    {{
      $t("funnel-flow.paid-social.creative-angle.button-label", {
        name: subcategoryName,
      })
    }}
  </Button>

  <CreativeAngleButtonModal
    v-if="isModalOpen"
    v-model="isModalOpen"
    :creativeAngle="creativeAngle"
  />
</template>
