<script setup lang="ts">
import { BrandTypography } from "@/services/NewBrandsApi";

interface Props {
  typography: BrandTypography;
}

defineProps<Props>();
</script>

<template>
  <CardBase v-for="font in typography.fonts" class="tw:p-3" borderRadius="sm">
    <!-- Category -->
    <Chip class="tw:mb-2.5" size="sm">
      {{ $t(`brands.settings.typography.usages.${font.usage}.title`) }}
    </Chip>

    <!-- Font family -->
    <h3 class="tw:mb-2 tw:font-bold">{{ typography.family }}</h3>

    <!-- Style -->
    <p class="tw:text-sm tw:text-gray-500 tw:capitalize">
      {{ font.style }}
    </p>
  </CardBase>
</template>
