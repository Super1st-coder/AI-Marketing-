<script setup lang="ts">
import { ImageLibrarySource } from "./image-library.types";

const props = defineProps<{
  page: string;
  options: ImageLibrarySource[];
}>();

const emit = defineEmits<{
  navigate: [slug: string];
}>();

function gotoPage(slug: string) {
  emit("navigate", slug);
}
</script>

<template>
  <div class="tw:p-6">
    <h2 class="tw:mb-12 tw:text-xl tw:font-bold">
      {{ $t("image-library.select-image-from") }}
    </h2>

    <SidebarLinkWrapper>
      <SidebarLink
        v-for="option in props.options"
        :icon="option.icon"
        :selected="props.page === option.slug"
        :variant="option.color"
        @click="gotoPage(option.slug)"
      >
        {{ option.label }}
      </SidebarLink>
    </SidebarLinkWrapper>
  </div>
</template>
