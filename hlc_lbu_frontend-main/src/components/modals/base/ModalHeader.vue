<script setup lang="ts">
import { modalScrollableInjectionKey } from "@/components/modals/base/useModalContext";

const scrollable = inject(
  modalScrollableInjectionKey,
  computed(() => "outer"),
);
</script>

<template>
  <div
    class="tw:p-4 tw:sm:p-6"
    :class="{
      'tw:border-b tw:border-gray-200': scrollable === 'inner',
    }"
  >
    <slot name="before" />

    <h2
      v-if="$slots.default"
      class="tw:mr-12 tw:text-2xl tw:font-bold"
      :class="{ 'tw:mb-2': $slots.description || $slots.after }"
    >
      <slot />
    </h2>

    <p v-if="$slots.description" class="tw:font-medium tw:text-gray-500">
      <slot name="description" />
    </p>

    <slot name="after" />
  </div>
</template>
