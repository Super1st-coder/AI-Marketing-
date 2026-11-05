<script setup lang="ts">
export interface FormStepLayoutProps {
  is?: string | Component;
  maxWidth?: string | number;
}

withDefaults(defineProps<FormStepLayoutProps>(), {
  is: "form",
  maxWidth: 1090,
});
</script>

<template>
  <component
    :is="is"
    class="tw:flex tw:min-h-[calc(100vh-66px-73px)] tw:flex-col"
  >
    <Container :maxWidth="maxWidth" class="tw:grow tw:py-10">
      <div class="tw:flex tw:flex-col tw:gap-5">
        <slot />
      </div>
    </Container>

    <div
      v-if="$slots.actions"
      class="tw:sticky tw:bottom-0 tw:border-t tw:border-divider tw:bg-white tw:py-6"
    >
      <Container :maxWidth="1312" class="tw:flex tw:justify-between tw:gap-5">
        <slot name="actions" />
      </Container>
    </div>
  </component>
</template>
