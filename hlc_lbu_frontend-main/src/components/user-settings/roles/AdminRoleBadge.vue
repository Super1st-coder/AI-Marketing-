<script setup lang="ts">
const { name, icon } = defineProps<{
  name: string;
  icon: string;
}>();

const { t, te } = useI18n();

const key = computed(() => `roles.${name}.title`);
</script>

<template>
  <div class="tw:flex tw:items-center tw:font-medium">
    <span class="tw:text-2xl">{{ icon }}</span>
    {{ te(key) ? t(key) : name }}
  </div>
</template>
