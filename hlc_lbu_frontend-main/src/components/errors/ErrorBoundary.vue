<script setup lang="ts">
const capturedError = defineModel<Error>({ required: false });

const route = useRoute();

onErrorCaptured((error) => {
  console.error(error);
  console.log(error.name);

  if ((error as any)?.name === "AuthRedirectError") {
    return false;
  }
  capturedError.value = error;

  return false;
});

watch(
  () => route.fullPath,
  () => {
    capturedError.value = undefined;
  },
);
</script>

<template>
  <template v-if="capturedError">
    <slot name="fallback" :error="capturedError" />
  </template>
  <template v-else>
    <slot></slot>
  </template>
</template>
