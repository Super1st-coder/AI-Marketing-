<script setup lang="ts">
import type { UploadDataSourceBody } from "@/services/NewBrandsApi";

const props = defineProps<{
  loaderSteps: string[];
  section: UploadDataSourceBody["section"];
  loaderInterval?: number;
  beforeSubmitFn?: () => Promise<void>;
  afterSubmitFn?: () => Promise<void>;
}>();

const isOpen = defineModel<boolean>({ required: true });

const screen = ref<"selection" | "manual" | "upload">("selection");
</script>

<template>
  <Modal v-if="screen === 'selection'" v-model="isOpen" :maxWidth="600">
    <ModalHeader>
      <slot name="title" />

      <template #description>
        <slot name="description" />
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-7">
      <CardButton icon="lucide:cloud-upload" @click="screen = 'upload'">
        <template #title>
          {{ $t("brands.settings.context-modal.upload-card-title") }}
        </template>

        <template #description>
          <slot name="uploadCardDescription" />
        </template>
      </CardButton>

      <CardButton icon="lucide:cloud-upload" @click="screen = 'manual'">
        <template #title>
          {{ $t("brands.settings.context-modal.manual-card-title") }}
        </template>

        <template #description>
          <slot name="manualCardDescription" />
        </template>
      </CardButton>
    </ModalBody>
  </Modal>
  <template v-else-if="screen === 'manual'">
    <slot />
  </template>
  <BrandFormAddContextModal
    v-else-if="screen === 'upload'"
    v-model="isOpen"
    :loaderSteps="loaderSteps"
    :loaderInterval="loaderInterval"
    :section="props.section"
    :beforeSubmitFn="beforeSubmitFn"
    :afterSubmitFn="afterSubmitFn"
  >
    <template #title>
      {{ $t("brands.settings.context-modal.upload-modal-title") }}
    </template>

    <template #description>
      <slot name="uploadDescription" />
    </template>

    <template #warning>
      <slot name="uploadWarning" />
    </template>
  </BrandFormAddContextModal>
</template>
