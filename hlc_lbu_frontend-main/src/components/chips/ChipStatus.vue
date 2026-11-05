<script lang="ts" setup>
defineProps<{
  status: "A" | "active" | "inactive" | "P" | "pending" | "I" | "inactive";
}>();
</script>

<template>
  <Chip
    :color="
      status === 'A' || status === 'active'
        ? 'success'
        : status === 'P' || status === 'pending'
          ? 'warning'
          : 'secondary'
    "
    variant="label"
    size="sm"
  >
    {{
      status === "A" || status === "active"
        ? $t("global.active")
        : status === "P" || status === "pending"
          ? $t("global.pending")
          : $t("global.inactive")
    }}
  </Chip>
</template>
