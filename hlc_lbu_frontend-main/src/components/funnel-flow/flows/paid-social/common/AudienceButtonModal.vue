<script setup lang="ts">
import { AudienceItem } from "@/services/projects/AudienceApi";

defineProps<{
  audience: AudienceItem;
  audienceType?: "preferred" | "generated" | "ads-experiment" | "saved";
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
      {{ audience.name }}
    </ModalHeader>

    <ModalBody>
      <CardBase class="tw:p-6">
        <AudiencePreview
          :audience="audience"
          :audienceType="audienceType"
          @removeComment="(_audience) => {}"
          displayActions
        />
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
