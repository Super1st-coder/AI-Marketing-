<script setup lang="ts">
defineProps<{ selected?: boolean }>();

const emit = defineEmits(["click"]);

const closeDropdown = inject<() => void>("closeDropdown");

function handleClick(e: MouseEvent) {
  closeDropdown?.();
  emit("click", e);
}
</script>

<template>
  <Button
    type="button"
    size="md"
    class="tw:justify-start! tw:text-left!"
    :color="selected ? 'primary' : 'secondary'"
    :variant="selected ? 'label' : 'text'"
    keepTextVariantPadding
    @click="handleClick"
  >
    <slot />
  </Button>
</template>
