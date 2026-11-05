<script setup lang="ts">
import { AdsExperimentByAdSetData } from "@/services/funnel-flow/paid-social/AdsExperiment";

defineProps<{
  creativeAngle: AdsExperimentByAdSetData;
}>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    scrollable="inner"
    v-slot="{ close }"
  >
    <ModalHeader>
      {{
        $te(
          `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(creativeAngle.subcategory.name)}.name`,
        )
          ? $t(
              `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(creativeAngle.subcategory.name)}.name`,
            )
          : creativeAngle.subcategory.name
      }}
    </ModalHeader>

    <ModalBody>
      <CardBase class="tw:p-6">
        <CreativeAnglePreview :creativeAngle="creativeAngle" />
      </CardBase>
    </ModalBody>

    <ModalFooter>
      <template #before>
        <Button
          color="primary"
          variant="outlined"
          @click="close"
          type="button"
          leftIcon="tabler-arrow-left"
        >
          {{ $t("global.back") }}
        </Button>
      </template>
    </ModalFooter>
  </Modal>
</template>
