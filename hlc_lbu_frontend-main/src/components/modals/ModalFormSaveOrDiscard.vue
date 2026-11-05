<script setup lang="ts">
const props = defineProps<{
  isDirty: boolean;
  saveFn: () => Promise<void>;
  disable?: boolean;
}>();

const isModalOpen = ref(false);
const resolveRef = ref<(value: SaveLockingResult) => void>();
const isSaving = ref(false);

async function handleOnLocked(): Promise<SaveLockingResult> {
  if (props.disable) {
    return undefined;
  }

  isModalOpen.value = true;

  return await new Promise<SaveLockingResult>((resolve) => {
    resolveRef.value = resolve;
  });
}

useSaveLock(() => props.isDirty, handleOnLocked);

function handleClose() {
  resolveRef.value?.("cancel");
  isModalOpen.value = false;
}

function handleCancel() {
  resolveRef.value?.("cancel");
  isModalOpen.value = false;
}

function handleDiscardChanges() {
  resolveRef.value?.("confirm");
  isModalOpen.value = false;
}

async function handleSaveAndExit() {
  isSaving.value = true;

  try {
    await props.saveFn();
    resolveRef.value?.("confirm");
    isModalOpen.value = false;
  } catch (error) {
    if (isAuthRedirectInProgress()) return;
    throw error;
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <ModalGeneric
    v-model="isModalOpen"
    name="saveAlert"
    :closeButton="!isSaving"
    :closeOnClickOutside="!isSaving"
    @close="handleClose"
  >
    <template #title>
      <slot name="title">
        {{ $t("modals.save-or-discard.title") }}
      </slot>
    </template>

    <template #description>
      <slot name="description">
        {{ $t("modals.save-or-discard.description") }}
      </slot>
    </template>

    <template #actions>
      <Button
        variant="outlined"
        color="secondary"
        type="button"
        :disabled="isSaving"
        @click="handleCancel"
      >
        <slot name="cancel">
          {{ $t("global.cancel") }}
        </slot>
      </Button>

      <Button
        variant="label"
        color="primary"
        type="button"
        :disabled="isSaving"
        @click="handleDiscardChanges"
      >
        <slot name="discardChanges">
          {{ $t("modals.save-or-discard.discard-changes") }}
        </slot>
      </Button>

      <Button type="button" :isLoading="isSaving" @click="handleSaveAndExit">
        <slot name="saveAndExit">
          {{ $t("modals.save-or-discard.save-and-exit") }}
        </slot>
      </Button>
    </template>
  </ModalGeneric>
</template>
