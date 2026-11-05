<script lang="ts" setup>
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <Button
    class="tw:shrink-0"
    size="md"
    color="primary"
    variant="label"
    icon="tabler-help"
    v-bind="$attrs"
    type="button"
  ></Button>

  <!-- TODO: create a tooltip with the text info -->
  <div class="tw:hidden">
    <slot />
  </div>
</template>
