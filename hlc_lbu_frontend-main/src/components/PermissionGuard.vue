<script setup lang="ts">
interface Props {
  requires: RoutePermissionMeta[];
  mode?: "all" | "any";
}

const props = withDefaults(defineProps<Props>(), { mode: "all" });
const authStore = useAuthStore();

const hasAccess = computed(() => {
  if (props.mode === "any") {
    return props.requires.some((p) => authStore.hasPermissionFor([p]));
  }

  return authStore.hasPermissionFor(props.requires);
});
</script>

<template>
  <slot v-if="hasAccess" :hasAccess="hasAccess" />
</template>
