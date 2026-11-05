<script setup lang="ts">
const emit = defineEmits<{ click }>();

async function handleClick() {
  if ((await useSaveLockingStore().execute()) === "cancel") return;

  emit("click");
}
</script>

<template>
  <Button
    v-if="$slots.default"
    variant="outlined"
    color="primary"
    leftIcon="tabler-arrow-left"
    type="button"
    @click="handleClick"
  >
    <slot />
  </Button>
  <Button
    v-else
    variant="outlined"
    color="primary"
    leftIcon="tabler-arrow-left"
    type="button"
    @click="handleClick"
  />
</template>
