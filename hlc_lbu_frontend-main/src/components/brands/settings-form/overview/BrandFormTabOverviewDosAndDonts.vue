<script setup lang="ts">
import type { BrandDosDont } from "@/services/NewBrandsApi";

interface Props {
  rule: BrandDosDont;
}

defineProps<Props>();
</script>

<template>
  <div class="tw:rounded-lg tw:bg-gray-100 tw:p-4">
    <!-- Image Preview -->
    <ImgFile
      v-if="rule.image_url"
      :src="rule.image_url"
      class="tw:mb-2.5 tw:shrink-0 tw:overflow-hidden tw:rounded-md tw:bg-gray-300 tw:object-cover tw:md:h-[100px] tw:md:w-[100px]"
    />

    <!-- Rule Text -->
    <p>
      {{ rule.rule }}
    </p>
  </div>
</template>
