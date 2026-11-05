<script lang="ts" setup>
defineProps<{ checked: boolean }>();
</script>

<template>
  <Button
    :icon="checked ? 'tabler-check' : 'undefined'"
    :color="checked ? 'primary' : 'secondary'"
    :variant="checked ? 'solid' : 'outlined'"
    size="sm"
  />
</template>
