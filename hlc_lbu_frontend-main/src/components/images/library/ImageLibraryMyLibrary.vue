<script setup lang="ts">
import { useImageLibraryStore } from "@/stores/ImageLibraryStore";

interface Props {
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  (e: "image-selected", payload: { url: string; photo: any }): void;
}>();

const query = ref("");
const isCropOpen = ref(false);
const selectedId = ref<string | null>(null);
const isLoadingForUpload = ref(false);
const errorMsg = ref<string | null>(null);

const imageTypeOpen = ref(false);
const imageType = ref<any | "">("");

const store = useImageLibraryStore();
const { t } = useI18n();

const photos = computed(() => store.images);

function filterImageType(type: string) {
  imageTypeOpen.value = false;
  imageType.value = type;
  store.resetImages();
  store.fetchImages(type, query.value);
}

const debouncedQuery = useDebounce(query, 400);

const selectedPhoto = computed(
  () => photos.value.find((p) => p.id === selectedId.value) || null,
);

const selectedDownloadUrl = computed(() => selectedPhoto.value?.url || "");

async function onUploadClick() {
  if (!selectedPhoto.value) return;
  const url = selectedDownloadUrl.value;
  if (!url || isLoadingForUpload.value) return;

  isLoadingForUpload.value = true;

  try {
    // Download image
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok)
      throw new Error(`Failed to download from Image Library: ${res.status}`);
    const blob = await res.blob();

    // Extract data from blob
    const name = selectedPhoto.value.id || "image-library";
    const mime = blob.type || "image/jpeg";
    const file = new File([blob], name, { type: mime });

    // Set file
    store.setSelectedFile(file, {
      id: selectedPhoto.value.id,
      cropped: true,
      source: "image-library",
    });
    emit("image-selected", { url, photo: selectedPhoto.value });
  } catch (e) {
    console.error(e);
    errorMsg.value = t("image-library.my-library.errors.upload-image");
  } finally {
  }
}

function selectPhoto(p: any) {
  selectedId.value = selectedId.value === p.id ? null : p.id;
}

function nextPage() {
  if (store.hasNextPage && !store.loadingImages) {
    store.nextPage();
  }
}

function prevPage() {
  if (store.hasPrevPage) {
    store.prevPage();
  }
}

onMounted(() => {
  store.resetImages();
  store.fetchImages();
});

watch(isCropOpen, (open) => {
  if (!open) {
    isLoadingForUpload.value = false;
  }
});

watch(debouncedQuery, async (val) => {
  store.resetImages();
  await store.fetchImages(imageType.value, val);
});
</script>

<template>
  <ImageLibraryTitle icon="tabler:books">
    {{ $t("image-library.sources.my-library") }}
  </ImageLibraryTitle>

  <Separator />

  <div class="tw:px-6 tw:pt-3 tw:pb-5">
    <div class="tw:pt-5 tw:pb-8">
      <div
        class="tw:mb-5 tw:flex tw:w-full tw:items-center tw:gap-2 tw:rounded-md tw:border tw:border-secondary/30 tw:px-3 tw:py-2"
      >
        <Icon icon="tabler-search" class="tw:text-xl" />
        <input
          v-model="query"
          :placeholder="$t('image-library.my-library.search-placeholder')"
          class="tw:text-x2 tw:w-full tw:outline-hidden"
          type="text"
        />
      </div>

      <div class="tw:relative tw:flex tw:gap-5">
        <Button
          variant="outlined"
          size="md"
          color="secondary"
          @click="imageTypeOpen = !imageTypeOpen"
        >
          <div class="tw:flex">
            <span>
              {{ $t("image-library.my-library.image-type-button") }}
            </span>
            <Icon icon="tabler-arrow-down" class="tw:ml-1 tw:text-xl" />
          </div>
        </Button>

        <div
          v-if="imageTypeOpen"
          tabindex="0"
          class="tw:absolute tw:top-10 tw:left-0 tw:z-20 tw:mt-2 tw:w-[190px] tw:rounded-md tw:border tw:border-secondary/30 tw:bg-white tw:shadow"
        >
          <ul class="tw:p-2">
            <li>
              <button
                @click="filterImageType('')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("global.any") }}
              </button>
            </li>
            <li>
              <button
                @click="filterImageType('buyer')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("buyer-person.image-library.select-option") }}
              </button>
            </li>
            <li>
              <button
                @click="filterImageType('product')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("products.image-library.select-option") }}
              </button>
            </li>
            <li>
              <button
                @click="filterImageType('umbrella')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("umbrella-campaign.image-library.select-option") }}
              </button>
            </li>
            <li>
              <button
                @click="filterImageType('campaign')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("campaigns.image-library.select-option") }}
              </button>
            </li>
            <li>
              <button
                @click="filterImageType('ads')"
                class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
              >
                {{ $t("ads.image-library.select-option") }}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <ImageLibraryImageGrid v-if="store.loadingImages">
      <div
        v-for="i in 12"
        :key="i"
        class="tw:h-[120px] tw:animate-pulse tw:rounded-xl tw:bg-secondary/20"
      ></div>
    </ImageLibraryImageGrid>
    <ImageLibraryImageGrid v-else-if="photos.length">
      <div
        v-for="p in photos"
        :key="p.id"
        class="tw:group tw:relative tw:h-full tw:cursor-pointer tw:overflow-hidden tw:rounded-xl"
        :class="{ 'tw:ring-2 tw:ring-primary': selectedId === p.id }"
        @click="selectPhoto(p)"
      >
        <img
          :src="p.url"
          :alt="p.id || $t('image-library.common.image-alt')"
          class="tw:h-[120px] tw:w-full tw:object-cover tw:transition-transform tw:group-hover:scale-105"
        />
        <div class="tw:h-full tw:bg-secondary tw:p-2 tw:text-sm tw:text-white">
          {{ p.description }}
        </div>

        <!-- Black -->
        <div
          v-if="selectedId === p.id"
          class="tw:absolute tw:inset-0 tw:bg-black/20"
        ></div>

        <!-- Check mark -->
        <div
          v-if="selectedId === p.id"
          class="tw:absolute tw:top-2 tw:right-2 tw:rounded-full tw:bg-primary tw:p-1 tw:text-white"
        >
          <Icon icon="tabler-check" />
        </div>
      </div>
    </ImageLibraryImageGrid>
    <div v-else class="tw:text-secondary">
      {{ $t("image-library.my-library.no-images-found") }}
    </div>
  </div>

  <Separator />

  <div class="tw:flex tw:w-full tw:justify-between tw:p-6">
    <div class="tw:flex tw:items-center tw:gap-2">
      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        :disabled="!store.hasPrevPage || store.loadingImages"
        leftIcon="tabler-chevron-left"
        @click="prevPage"
      >
        {{ $t("image-library.common.prev") }}
      </Button>

      <span class="tw:text-sm tw:text-secondary-text">
        {{
          $t("image-library.common.page", {
            current: store.currentPage,
            total: store.pages || 1,
          })
        }}
      </span>

      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        :disabled="!store.hasNextPage || store.loadingImages"
        icon="tabler-chevron-right"
        @click="nextPage"
      >
        {{ $t("image-library.common.next") }}
      </Button>
    </div>

    <Button
      :disabled="!selectedPhoto || isLoadingForUpload"
      :isLoading="store.loadingImages || isLoadingForUpload"
      @click="onUploadClick"
    >
      {{ $t("image-library.common.upload-image") }}
    </Button>
  </div>
</template>
