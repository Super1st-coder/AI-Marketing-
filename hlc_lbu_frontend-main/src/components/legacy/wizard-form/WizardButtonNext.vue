<template>
  <Button icon="tabler-arrow-narrow-right" class="tw:basis-[300px]">
    <template v-if="$slots.default">
      <slot />
    </template>
    <template v-else>
      {{ $t("global.next") }}
    </template>
  </Button>
</template>
