<script setup lang="ts">
import ImageLibraryMenuSidebar from "./ImageLibraryMenuSidebar.vue";
import ImageLibraryMyLibrary from "./ImageLibraryMyLibrary.vue";
import ImageLibraryUpload from "./ImageLibraryUpload.vue";
import ImageLibraryUnsplash from "./ImageLibraryUnsplash.vue";
import ImageLibraryGoogleDriveAdmin from "./ImageLibraryGoogleDriveAdmin.vue";
import { ImageLibrarySource } from "./image-library.types.ts";

const { t } = useI18n();

const props = defineProps<{
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
  customSources?: ImageLibrarySource[];
}>();

const menuOptions = computed<ImageLibrarySource[]>(() => [
  {
    slug: "my-library",
    label: t("image-library.sources.my-library"),
    icon: "tabler-books",
    cropper: false,
    component: ImageLibraryMyLibrary,
  },
  {
    slug: "upload",
    label: t("image-library.sources.upload"),
    icon: "tabler-download",
    cropper: props.cropper,
    component: ImageLibraryUpload,
  },
  {
    slug: "unsplash",
    label: t("image-library.sources.unsplash"),
    icon: "tabler-brand-unsplash",
    cropper: props.cropper,
    component: ImageLibraryUnsplash,
  },
  {
    slug: "google-drive",
    label: t("image-library.sources.google-drive"),
    icon: "tabler-brand-google-drive",
    cropper: props.cropper,
    component: ImageLibraryGoogleDriveAdmin,
  },
  ...(props.customSources ? props.customSources : []),
]);

const page = ref<ImageLibrarySource["slug"]>("my-library");

const selected = computed<ImageLibrarySource>(
  () =>
    menuOptions.value.find((o) => o.slug === page.value) ??
    menuOptions.value[0],
);

function gotoPage(pageSlug: string) {
  page.value = pageSlug;
}
</script>

<template>
  <div class="tw:grid tw:grid-cols-1 tw:md:grid-cols-12">
    <div
      class="tw:border-b tw:border-gray-300 tw:md:col-span-3 tw:md:border-r tw:md:border-b-0"
    >
      <ImageLibraryMenuSidebar
        :page="page"
        :options="menuOptions"
        @navigate="gotoPage"
      />
    </div>

    <div class="tw:md:col-span-9">
      <component
        v-if="selected.component"
        :is="selected.component"
        v-bind="{
          accept: props.accept,
          cropper: selected.cropper,
          aspectRatio: props.aspectRatio,
          disabled: props.disabled,
        }"
      />
      <slot v-else :name="`source:${selected.slug}`" />
    </div>
  </div>
</template>
