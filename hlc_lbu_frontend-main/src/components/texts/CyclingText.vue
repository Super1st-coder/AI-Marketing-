<script setup lang="ts">
interface Props {
  texts?: string[];
  interval?: number;
}

const props = withDefaults(defineProps<Props>(), {
  texts: () => [],
  interval: 1000,
});

const counter = useInterval(() => props.interval);

const currentText = computed(() => {
  if (props.texts.length === 0) return undefined;

  return props.texts[counter.value % props.texts.length];
});
</script>

<template>
  <span>{{ currentText }}</span>
</template>
