<script lang="ts" setup>
const store = useMenusStore();
</script>

<template>
  <button @click="store.toggleMenuExpanded">
    <Icon icon="tabler:layout-sidebar" class="tw:text-xl tw:text-gray-500" />
  </button>
</template>
