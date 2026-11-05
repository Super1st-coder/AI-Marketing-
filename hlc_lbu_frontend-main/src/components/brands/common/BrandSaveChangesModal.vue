<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  cancel: [];
  confirmWithAnalysis: [];
  confirmWithoutAnalysis: [];
}>();

const isLoading = ref(false);
const selectedOption = ref<"withoutAnalysis" | "withAnalysis">("withAnalysis");

async function handleCancel() {
  emit("cancel");
}

async function handleConfirmWithoutAnalysis() {
  isLoading.value = true;
  selectedOption.value = "withoutAnalysis";

  emit("confirmWithoutAnalysis");
}

async function handleConfirmWithAnalysis() {
  emit("confirmWithAnalysis");
  selectedOption.value = "withAnalysis";

  isLoading.value = true;
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="660"
    @cancel="handleCancel"
    @close="handleCancel"
    :closeButton="!isLoading"
    :closeOnClickOutside="!isLoading"
  >
    <template #title>
      {{ $t("brands.settings.save-changes-modal.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.save-changes-modal.description") }}
    </template>

    <template #actions>
      <Button
        variant="outlined"
        color="secondary"
        type="button"
        :disabled="isLoading"
        @click="handleCancel"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button
        variant="outlined"
        type="button"
        :disabled="isLoading"
        :isLoading="isLoading && selectedOption === 'withoutAnalysis'"
        @click="handleConfirmWithoutAnalysis"
      >
        {{ $t("brands.settings.save-changes-modal.update-without-analysis") }}
      </Button>

      <Button
        type="button"
        :disabled="isLoading"
        :isLoading="isLoading && selectedOption === 'withAnalysis'"
        @click="handleConfirmWithAnalysis"
      >
        {{ $t("brands.settings.save-changes-modal.update-and-reanalyze") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
