<script setup lang="ts">
const props = defineProps<{ isDirty: boolean; disable?: boolean }>();

const isModalOpen = ref(false);
const resolveRef = ref<(value: SaveLockingResult) => void>();

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

function handleCancel() {
  resolveRef.value?.("cancel");
  isModalOpen.value = false;
}

function handleContinue() {
  resolveRef.value?.("confirm");
  isModalOpen.value = false;
}
</script>

<template>
  <ModalGeneric
    v-model="isModalOpen"
    name="saveAlert"
    @cancel="handleCancel"
    @confirm="handleContinue"
    @close="handleCancel"
  >
    <template #title>
      {{ $t("modals.save-alert.title") }}
    </template>

    <template #description>
      {{ $t("modals.save-alert.description") }}
    </template>

    <template #cancel>
      {{ $t("global.stay") }}
    </template>
    <template #continue>
      {{ $t("global.leave") }}
    </template>
  </ModalGeneric>
</template>
