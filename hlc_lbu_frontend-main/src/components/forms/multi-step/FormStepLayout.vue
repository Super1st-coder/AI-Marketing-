<script lang="ts" setup>
import { ContainerProps } from "@/components/backgrounds/Container.vue";

export interface FormStepLayoutProps extends ContainerProps {
  as?: string;
  disabled?: boolean;
}

withDefaults(defineProps<FormStepLayoutProps>(), { as: "form" });

onMounted(() => {
  scrollWindowToTop();
});
</script>

<template>
  <component :is="as" class="tw:flex tw:h-full tw:w-full tw:flex-col">
    <div
      v-if="$slots.stepper"
      class="tw:border-b tw:border-divider tw:px-7 tw:py-2"
    >
      <slot name="stepper" />
    </div>

    <Container
      v-if="$slots.default"
      class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:py-6 tw:pb-12"
      :class="{ 'tw:pointer-events-none tw:opacity-50': disabled }"
      :maxWidth="maxWidth"
    >
      <slot />
    </Container>

    <slot name="custom" />

    <div
      v-if="$slots.actions"
      class="tw:sticky tw:bottom-0 tw:border-t tw:border-divider tw:bg-white tw:p-6"
    >
      <Container>
        <slot name="actions" />
      </Container>
    </div>
  </component>
</template>
