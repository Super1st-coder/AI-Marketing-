<script setup lang="ts">
import { BrandLogo } from "@/services/NewBrandsApi";

interface Props {
  logo: BrandLogo;
}

defineProps<Props>();
</script>

<template>
  <div>
    <!-- Logo Preview -->
    <CardBase
      class="tw:mb-2.5 tw:aspect-75/35 tw:overflow-hidden"
      color="secondary"
      borderRadius="xs"
    >
      <!-- Filled State -->
      <ImgFile
        v-if="logo.image_url"
        :src="logo.image_url"
        class="tw:h-full tw:w-full tw:object-contain"
      />
    </CardBase>

    <!-- Header -->
    <h3 class="tw:font-bold">
      {{
        logo.category === "custom" && logo.category_alias
          ? logo.category_alias
          : $t(`brands.settings.logos.categories.${logo.category}.title`)
      }}
    </h3>
  </div>
</template>
