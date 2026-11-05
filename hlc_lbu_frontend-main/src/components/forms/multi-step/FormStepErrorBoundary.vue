<script lang="ts" setup>
const capturedError = ref<Error>();
</script>

<template>
  <ErrorBoundary v-model="capturedError">
    <slot />

    <template #fallback="{ error }">
      <ErrorScreen :error="error">
        <template #actions>
          <Button type="submit" @click="capturedError = undefined">
            {{ $t("global.try-again") }}
          </Button>
        </template>
      </ErrorScreen>
    </template>
  </ErrorBoundary>
</template>
