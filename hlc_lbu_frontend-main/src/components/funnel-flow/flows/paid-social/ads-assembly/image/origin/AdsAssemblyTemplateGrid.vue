<script setup lang="ts">
import { AdMediaTemplate } from "@/services/funnel-flow/paid-social/AdsApi";

defineProps<{ templates: AdMediaTemplate[] }>();
</script>

<template>
  <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:md:grid-cols-4">
    <CardBase
      v-for="template in templates"
      class="tw:grid tw:grid-cols-1 tw:gap-2.5 tw:p-3"
    >
      <h3 class="tw:text-sm tw:font-semibold">
        {{ template.template_name }}
      </h3>

      <img
        :src="template.template_preview_url"
        class="tw:aspect-square tw:w-full tw:rounded-xl tw:bg-gray-500"
      />

      <Chip class="tw:place-self-start">
        {{ $t("funnel-flow.paid-social.ads.origin.template-type.static") }}
      </Chip>
    </CardBase>
  </div>
</template>
