<script setup lang="ts">
import ImagenLibraryApi from "@/services/ImagenLibraryApi";
import type { UnsplashPhoto } from "@/types/unsplash";
import ModalImageCropper from "@/components/modals/ModalImageCropper.vue";
import { useObjectUrl } from "@vueuse/core";
import { object, string } from "yup";

interface Props {
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
}
const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "image-selected", payload: { url: string; photo: UnsplashPhoto }): void;
}>();

const store = useImageLibraryStore();
const { t } = useI18n();

const currentView = ref<"gallery" | "confirm">("gallery");
const query = ref("");
const page = ref(1);
const perPage = ref(12);
const total = ref(0);
const totalPages = ref(0);
const photos = ref<UnsplashPhoto[]>([]);
const loading = ref(false);
const errorMsg = ref<string | null>(null);
const selectedId = ref<string | null>(null);
const selectedPhoto = computed(
  () => photos.value.find((p) => p.id === selectedId.value) || null,
);
const selectedDownloadUrl = computed(() => {
  const p = selectedPhoto.value;
  if (!p) return "";
  return (
    p.urls.full ||
    p.urls.raw ||
    p.urls.regular ||
    p.urls.small ||
    p.urls.thumb ||
    ""
  );
});

const isCropOpen = ref(false);
const cropFile = ref<File | null>(null);
const croppedFile = ref<File | null>(null);
const previewUrl = useObjectUrl(croppedFile);
const customName = ref("");
const customNameError = ref("");
const isLoadingForUpload = ref(false);

const MIN_SPIN_MS = 400;
function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const debouncedQuery = useDebounce(query, 400);
watch(debouncedQuery, () => {
  page.value = 1;
  fetchPhotos();
});
watch(page, () => {
  if (debouncedQuery.value) fetchPhotos();
});

async function fetchPhotos() {
  loading.value = true;
  errorMsg.value = null;
  try {
    const term = debouncedQuery.value;
    if (!term) {
      photos.value = [];
      total.value = 0;
      totalPages.value = 0;
      return;
    }
    const resp = await ImagenLibraryApi.getUnsplashImages(
      perPage.value,
      page.value,
      term,
      {
        orientation: orientation.value || undefined,
        color: color.value || undefined,
      },
    );
    photos.value = resp.results ?? [];
    total.value = resp.total ?? 0;
    totalPages.value = resp.total_pages ?? 0;
  } catch (err: any) {
    errorMsg.value = t("image-library.unsplash.errors.load-images");
  } finally {
    loading.value = false;
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value += 1;
    fetchPhotos();
  }
}

function prevPage() {
  if (page.value > 1) {
    page.value -= 1;
    fetchPhotos();
  }
}

function selectPhoto(p: UnsplashPhoto) {
  selectedId.value = selectedId.value === p.id ? null : p.id;
}

async function onUploadClick() {
  if (!selectedPhoto.value) return;
  const url = selectedDownloadUrl.value;
  if (!url) return;

  try {
    if (isLoadingForUpload.value) return;
    isLoadingForUpload.value = true;
    const startedAt = Date.now();

    // Download image
    const res: Response = await fetch(url);
    if (!res.ok)
      throw new Error(`Failed to download Unsplash image: ${res.status}`);
    const blob = await res.blob();

    // Extract data from blob
    const name = selectedPhoto.value.id || "unsplash";
    const mime = blob.type && blob.type !== "" ? blob.type : "image/jpeg";
    const file = new File([blob], `${name}.jpg`, { type: mime });

    if (props.cropper) {
      cropFile.value = file;
      await nextTick();
      isCropOpen.value = true;
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_SPIN_MS) await wait(MIN_SPIN_MS - elapsed);
      isLoadingForUpload.value = false;
    } else {
      croppedFile.value = file;
      customName.value = file.name.replace(/\.[^/.]+$/, "");
      currentView.value = "confirm";
      isLoadingForUpload.value = false;
    }
  } catch (e) {
    console.error(e);
  } finally {
    if (!isCropOpen.value) {
      isLoadingForUpload.value = false;
    }
  }
}

function handleSaveCrop(f: File) {
  isCropOpen.value = false;
  cropFile.value = null;
  croppedFile.value = f;
  customName.value = f.name.replace(/\.[^/.]+$/, "");
  currentView.value = "confirm";
}

async function confirmSelection() {
  if (!croppedFile.value) return;

  try {
    await object({
      customName: string()
        .trim()
        .required(t("image-library.common.image-name-required")),
    }).validate({ customName: customName.value });
    customNameError.value = "";
  } catch (err: any) {
    customNameError.value = err.message;
    return;
  }

  const dot = croppedFile.value.name.lastIndexOf(".");
  const name = customName.value?.trim() || croppedFile.value.name.slice(0, dot);
  const renamed = new File([croppedFile.value], name, {
    type: croppedFile.value.type,
  });

  store.setSelectedFile(renamed, { cropped: true, source: "unsplash" });
  emit("image-selected", {
    url: URL.createObjectURL(renamed),
    photo: selectedPhoto.value!,
  });

  currentView.value = "gallery";
  croppedFile.value = null;
}

function cancelConfirm() {
  currentView.value = "gallery";
  croppedFile.value = null;
}

type Orientation = "landscape" | "portrait" | "squarish";
type Color =
  | "black_and_white"
  | "black"
  | "white"
  | "yellow"
  | "orange"
  | "red"
  | "purple"
  | "magenta"
  | "green"
  | "teal"
  | "blue";

const colorKeyMap: Record<Color, string> = {
  black_and_white: "black-and-white",
  black: "black",
  white: "white",
  yellow: "yellow",
  orange: "orange",
  red: "red",
  purple: "purple",
  magenta: "magenta",
  green: "green",
  teal: "teal",
  blue: "blue",
};

const orientation = ref<Orientation | "">("");
const color = ref<Color | "">("");
const orientationOpen = ref(false);
const colorOpen = ref(false);

const orientationLabel = computed(() =>
  orientation.value
    ? `:${t(`image-library.unsplash.orientations.${orientation.value}`)}`
    : `:${t("global.any")}`,
);
const colorLabel = computed(() =>
  color.value
    ? `:${t(`image-library.unsplash.colors.${colorKeyMap[color.value]}`)}`
    : `:${t("global.any")}`,
);

function openOrientation() {
  orientationOpen.value = !orientationOpen.value;
  colorOpen.value = false;
}
function openColor() {
  colorOpen.value = !colorOpen.value;
  orientationOpen.value = false;
}
function selectOrientation(o: Orientation | "") {
  orientation.value = o;
  page.value = 1;
  orientationOpen.value = false;
  if (debouncedQuery.value) fetchPhotos();
}
function selectColor(c: Color | "") {
  color.value = c;
  page.value = 1;
  colorOpen.value = false;
  if (debouncedQuery.value) fetchPhotos();
}
</script>

<template>
  <div>
    <ModalImageCropper
      v-if="props.cropper && cropFile"
      v-model="isCropOpen"
      :imageFile="cropFile"
      :aspectRatio="props.aspectRatio"
      @save="handleSaveCrop"
    />

    <template v-if="currentView === 'gallery'">
      <ImageLibraryTitle icon="tabler:brand-unsplash">
        {{ $t("image-library.sources.unsplash") }}
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
              :placeholder="$t('image-library.unsplash.search-placeholder')"
              class="tw:text-x2 tw:w-full tw:outline-hidden"
              type="text"
            />
          </div>
          <div class="tw:relative">
            <ImageLibraryUnsplashButtons
              :orientation-label="orientationLabel"
              :color-label="colorLabel"
              order-by-label=":any"
              @open-orientation="openOrientation"
              @open-color="openColor"
              @open-order-by="() => {}"
            />

            <!-- Orientation menu -->
            <div
              v-if="orientationOpen"
              class="tw:absolute tw:z-10 tw:mt-2 tw:w-[260px] tw:rounded-md tw:border tw:border-secondary/30 tw:bg-white tw:shadow"
            >
              <ul class="tw:p-2">
                <li>
                  <button
                    class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
                    @click="selectOrientation('')"
                  >
                    {{ $t("global.any") }}
                  </button>
                </li>
                <li>
                  <button
                    class="tw:w-full tw:rounded tw:px-3 tw:py-2 tw:hover:bg-secondary/10"
                    @click="selectOrientation('landscape')"
                  >
                    {{ $t("image-library.unsplash.orientations.landscape") }}
                  </button>
                </li>
                <li>
                  <button
                    class="hover:tw:bg-secondary/10 tw:w-full tw:rounded tw:px-3 tw:py-2"
                    @click="selectOrientation('portrait')"
                  >
                    {{ $t("image-library.unsplash.orientations.portrait") }}
                  </button>
                </li>
                <li>
                  <button
                    class="hover:tw:bg-secondary/10 tw:w-full tw:rounded tw:px-3 tw:py-2"
                    @click="selectOrientation('squarish')"
                  >
                    {{ $t("image-library.unsplash.orientations.squarish") }}
                  </button>
                </li>
              </ul>
            </div>

            <!-- Color menu -->
            <div
              v-if="colorOpen"
              class="tw:absolute tw:left-[220px] tw:z-10 tw:mt-2 tw:w-[260px] tw:rounded-md tw:border tw:border-secondary/30 tw:bg-white tw:shadow"
            >
              <ul class="tw:max-h-60 tw:overflow-auto tw:p-2">
                <li>
                  <button
                    class="hover:tw:bg-secondary/10 tw:w-full tw:rounded tw:px-3 tw:py-2"
                    @click="selectColor('')"
                  >
                    {{ $t("global.any") }}
                  </button>
                </li>
                <li
                  v-for="c in [
                    'black_and_white',
                    'black',
                    'white',
                    'yellow',
                    'orange',
                    'red',
                    'purple',
                    'magenta',
                    'green',
                    'teal',
                    'blue',
                  ]"
                  :key="c"
                >
                  <button
                    class="hover:tw:bg-secondary/10 tw:w-full tw:rounded tw:px-3 tw:py-2"
                    @click="selectColor(c as Color)"
                  >
                    {{
                      $t(
                        `image-library.unsplash.colors.${colorKeyMap[c as Color]}`,
                      )
                    }}
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Loading -->
        <ImageLibraryImageGrid v-if="loading">
          <div
            v-for="i in perPage"
            :key="i"
            class="tw:h-[120px] tw:animate-pulse tw:rounded-xl tw:bg-secondary/20"
          ></div>
        </ImageLibraryImageGrid>
        <!-- Images -->
        <ImageLibraryImageGrid v-else-if="photos.length">
          <div
            v-for="p in photos"
            :key="p.id"
            class="tw:group tw:relative tw:cursor-pointer tw:overflow-hidden tw:rounded-xl"
            :class="{ 'tw:ring-2 tw:ring-primary': selectedId === p.id }"
            @click="selectPhoto(p)"
          >
            <img
              :src="p.urls.small || p.urls.thumb"
              :alt="
                p.alt_description ||
                p.description ||
                $t('image-library.unsplash.image-alt')
              "
              class="tw:h-[120px] tw:w-full tw:object-cover tw:transition-transform tw:group-hover:scale-105"
            />
            <div
              v-if="selectedId === p.id"
              class="tw:absolute tw:inset-0 tw:bg-black/20"
            ></div>
            <div
              v-if="selectedId === p.id"
              class="tw:absolute tw:top-2 tw:right-2 tw:rounded-full tw:bg-primary tw:p-1 tw:text-white"
            >
              <Icon icon="tabler-check" />
            </div>
          </div>
        </ImageLibraryImageGrid>

        <div v-else class="tw:text-secondary">
          {{ $t("image-library.unsplash.type-to-search-images") }}
        </div>

        <div v-if="errorMsg" class="tw:text-red-500 tw:mt-3">
          {{ errorMsg }}
        </div>
      </div>

      <!-- Navegación y Upload -->
      <Separator />

      <div class="tw:flex tw:w-full tw:justify-between tw:p-6">
        <div class="tw:flex tw:items-center tw:gap-2">
          <Button
            variant="outlined"
            color="secondary"
            size="sm"
            :disabled="page <= 1 || loading"
            leftIcon="tabler-chevron-left"
            @click="prevPage"
          >
            {{ $t("image-library.common.prev") }}
          </Button>

          <span class="tw:text-sm">
            {{
              $t("image-library.common.page", {
                current: page,
                total: Math.max(totalPages, 1),
              })
            }}
          </span>

          <Button
            variant="outlined"
            color="secondary"
            size="sm"
            :disabled="page >= totalPages || loading"
            icon="tabler-chevron-right"
            @click="nextPage"
          >
            {{ $t("image-library.common.next") }}
          </Button>
        </div>

        <Button
          :disabled="!selectedPhoto || isLoadingForUpload"
          :isLoading="loading || isLoadingForUpload"
          @click="onUploadClick"
        >
          {{ $t("image-library.common.upload-image") }}
        </Button>
      </div>
    </template>

    <template v-else-if="currentView === 'confirm'">
      <div class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:p-6">
        <h2 class="tw:text-xl tw:font-bold">
          {{ $t("image-library.common.confirm-image") }}
        </h2>

        <div class="tw:w-full tw:max-w-[420px]">
          <FieldText
            v-model="customName"
            name="custom_name"
            :label="$t('image-library.common.image-name')"
            :placeholder="$t('image-library.common.enter-image-name')"
            required
          />
          <p v-if="customNameError" class="tw:mt-1 tw:text-sm tw:text-error">
            {{ customNameError }}
          </p>
        </div>

        <div
          class="tw:w-full tw:max-w-[420px] tw:overflow-hidden tw:rounded-lg tw:border tw:border-secondary/20"
        >
          <img
            :src="previewUrl"
            :alt="$t('image-library.common.cropped-preview-alt')"
            class="tw:h-auto tw:w-full tw:object-cover"
          />
        </div>

        <div
          v-if="croppedFile"
          class="tw:text-center tw:text-sm tw:text-secondary"
        >
          <strong>{{ croppedFile.name }}</strong>
          <span class="tw:ml-1">
            ({{ Math.ceil(croppedFile.size / 1024) }} KB)
          </span>
        </div>

        <div class="tw:mt-4 tw:flex tw:gap-3">
          <Button color="primary" @click="confirmSelection">
            {{ $t("image-library.common.use-this-image") }}
          </Button>
          <Button variant="outlined" color="secondary" @click="cancelConfirm">
            {{ $t("image-library.common.change-image") }}
          </Button>
        </div>
      </div>
    </template>
  </div>
</template>
