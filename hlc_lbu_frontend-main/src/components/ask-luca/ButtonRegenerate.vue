<script setup lang="ts" generic="T">
interface Props {
  fetcher: () => Promise<T>;
  regenerate?: boolean;
}

defineProps<Props>();
</script>

<template>
  <ButtonGenerateIdea
    type="button"
    :leftIcon="regenerate ? 'tabler-refresh' : undefined"
    :fetcher="fetcher"
  >
    <slot>
      <slot v-if="regenerate" name="regenerate">
        {{ $t("global.regenerate") }}
      </slot>
      <slot v-else name="generate">
        {{ $t("global.generate") }}
      </slot>
    </slot>
  </ButtonGenerateIdea>
</template>
