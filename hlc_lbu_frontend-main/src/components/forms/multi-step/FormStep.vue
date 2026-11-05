<script lang="ts" setup>
interface Props {
  name: string;
}

defineProps<Props>();
const { currentFlatStep } = useMultiStepFormContext();
</script>

<template>
  <div v-if="currentFlatStep.name === name" class="tw:flex tw:h-full">
    <FormStepErrorBoundary>
      <Suspense suspensible>
        <slot />

        <template #fallback>
          <CircleLoaderDefault class="tw:min-h-[calc(100vh-66px)] tw:w-full" />
        </template>
      </Suspense>
    </FormStepErrorBoundary>
  </div>
</template>
