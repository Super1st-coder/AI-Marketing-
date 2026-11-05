<script setup lang="ts">
import { provide } from "vue";
import { tabsValueInjectionKey } from "./useTabsContext";

interface TabsProps {
  defaultTab?: string | number;
  variant?: "default" | "buttonGroup";
  alignment?: "start" | "center" | "end";
  size?: "sm" | "lg";
  keepOnUnmount?: boolean;
}

const props = withDefaults(defineProps<TabsProps>(), {
  variant: "default",
  alignment: "start",
  size: "sm",
  keepOnUnmount: false,
});

const current = defineModel<string | number | undefined>({ required: false });

if (props.defaultTab) {
  current.value = props.defaultTab;
}

const variant = computed(() => props.variant);
const alignment = computed(() => props.alignment);
const size = computed(() => props.size);
const keepOnUnmount = computed(() => props.keepOnUnmount);

provide(tabsValueInjectionKey, {
  current: current,
  variant: variant,
  alignment: alignment,
  size: size,
  keepOnUnmount: keepOnUnmount,
});
</script>

<template>
  <div class="tw:h-full">
    <TabsList v-if="$slots.list">
      <slot name="list" />
    </TabsList>

    <slot />
  </div>
</template>
