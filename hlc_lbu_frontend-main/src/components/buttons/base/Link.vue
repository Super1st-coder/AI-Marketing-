<script lang="ts" setup>
import { RouteLocationRaw, RouterLink } from "vue-router";
import { LinkBaseProps } from "./LinkBase.vue";

export interface LinkProps extends LinkBaseProps {
  is?: string | Component;
  external?: boolean;
  to?: RouteLocationRaw;
}

withDefaults(defineProps<LinkProps>(), {
  is: RouterLink,
  external: false,
});
</script>

<template>
  <!-- Anchor or any other tag -->
  <LinkBase
    v-if="external || is !== RouterLink"
    v-bind="$props"
    :is="external ? 'a' : is"
    :target="external ? '_blank' : undefined"
    :type="is === 'button' ? 'button' : underline"
  >
    <slot />
  </LinkBase>
  <!-- Router link -->
  <LinkBase v-else v-bind="$props" :is="RouterLink">
    <slot />
  </LinkBase>
</template>
