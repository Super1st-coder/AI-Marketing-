<script setup lang="ts">
import { AudienceItem } from "@/services/projects/AudienceApi";

defineProps<{
  audience?: AudienceItem;
}>();

const isModalOpen = ref(false);
</script>

<template>
  <Button
    variant="outlined"
    color="secondary"
    size="xs"
    @click="isModalOpen = true"
    :shadow="false"
    :uppercase="false"
  >
    {{
      $t("funnel-flow.paid-social.audience.button-label", {
        name: audience?.name ?? "-",
      })
    }}
  </Button>

  <AudienceButtonModal
    v-if="isModalOpen && audience"
    v-model="isModalOpen"
    :audience="audience"
  />
</template>
