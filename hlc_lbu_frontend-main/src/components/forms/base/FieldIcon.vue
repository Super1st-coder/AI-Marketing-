<script lang="ts" setup>
interface Props {
  icon?: string;
  clickable?: boolean;
  iconClass?: ClassName;
}

withDefaults(defineProps<Props>(), {
  iconClass: "tw:text-gray-400",
});

const emit = defineEmits<{
  click: [e: MouseEvent];
}>();
</script>

<template>
  <button
    v-if="icon && clickable"
    type="button"
    class="tw:flex tw:items-center"
    @click="emit('click', $event)"
  >
    <Icon :icon="icon" class="tw:text-xl" :class="iconClass" />
  </button>

  <Icon v-else-if="icon" :icon="icon" class="tw:text-xl" :class="iconClass" />
</template>
