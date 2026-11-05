<script setup lang="ts">
import { BrandFormColor } from "../BrandFormTabColors.vue";

interface Props {
  color: BrandFormColor;
}

defineProps<Props>();
</script>

<template>
  <div>
    <!-- Swatch -->
    <CardBase
      class="tw:mb-3 tw:aspect-3/1"
      :style="{ backgroundColor: color.hex }"
      borderRadius="xs"
    ></CardBase>

    <!-- Name -->
    <h5 class="tw:mb-1 tw:text-sm tw:font-medium">{{ color.name }}</h5>

    <!-- Hex -->
    <p class="tw:text-sm tw:text-gray-500">{{ color.hex }}</p>
  </div>
</template>
