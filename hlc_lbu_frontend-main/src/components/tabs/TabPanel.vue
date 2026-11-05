<script setup lang="ts">
import { computed, ref } from "vue";
import { useTabsContext } from "./useTabsContext";

const props = defineProps<{
  value: string | number;
  useSuspense?: boolean;
}>();

const tabsContext = useTabsContext();

const { current } = tabsContext ?? {
  current: ref(undefined),
};

const keepOnUnmount = computed(() => tabsContext?.keepOnUnmount.value ?? false);

const isActive = computed(() => current.value && current.value === props.value);
const capturedError = ref<Error>();
</script>

<template>
  <div
    v-if="keepOnUnmount ? true : isActive"
    v-show="keepOnUnmount ? isActive : true"
  >
    <template v-if="useSuspense">
      <ErrorBoundary v-model="capturedError">
        <Suspense suspensible :timeout="0">
          <slot />

          <template #fallback>
            <CircleLoaderDefault class="tw:w-full tw:p-8" />
          </template>
        </Suspense>

        <template #fallback="{ error }">
          <ErrorScreen :error="error" useDefaultAction />
        </template>
      </ErrorBoundary>
    </template>
    <template v-else>
      <slot />
    </template>
  </div>
</template>
