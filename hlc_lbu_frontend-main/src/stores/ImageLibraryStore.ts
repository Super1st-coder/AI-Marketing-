import { defineStore } from "pinia";
import ImagenLibraryApi from "@/services/ImagenLibraryApi";
import { UnidentifiedError } from "@/services/common-errors";

type ImageLibrarySource =
  | "upload"
  | "unsplash"
  | "gdrive"
  | "ia"
  | "image-library";

type ImageLibraryBase = {
  raw: boolean;
  librarySource: ImageLibrarySource;
};

type ImageLibraryFileRaw = {
  raw: true;
  librarySource: "upload" | "unsplash" | "gdrive" | "ia";
};

type ImageLibraryFileFromLibrary = {
  raw: false;
  libraryId: string;
  librarySource: "image-library";
};

export type ImageLibraryFile = File &
  ImageLibraryBase &
  (ImageLibraryFileRaw | ImageLibraryFileFromLibrary);

export const useImageLibraryStore = defineStore("imageLibrary", () => {
  const loadingFromUrl = ref(false);
  const error = ref<string | null>(null);

  const selectedFile = ref<ImageLibraryFile | undefined>(undefined);

  const activeTarget = ref<Symbol | undefined>(undefined);
  const lastTarget = ref<Symbol | undefined>(undefined);
  const brandId = useBrandId();

  function setActiveTarget(id: Symbol | undefined) {
    activeTarget.value = id;
  }

  function setSelectedFile(
    file: File,
    opts: {
      id?: string;
      cropped?: boolean;
      source?: ImageLibrarySource;
    },
  ) {
    if (!opts.source) {
      throw new UnidentifiedError();
    }

    if (opts.source === "image-library" && !opts.id) {
      throw new UnidentifiedError();
    }

    if (!(file instanceof File)) {
      throw new UnidentifiedError();
    }

    let finalFile: ImageLibraryFile | undefined = undefined;

    if (opts.source === "image-library") {
      finalFile = Object.assign(file, {
        raw: false as const,
        libraryId: opts.id!,
        librarySource: opts.source,
      });
    } else {
      finalFile = Object.assign(file, {
        raw: true as const,
        librarySource: opts.source,
      });
    }

    error.value = null;
    selectedFile.value = finalFile;
    lastTarget.value = activeTarget.value;
  }

  const limit = ref(8);
  const start = ref(0);
  const total = ref(0);
  const images = ref<any[]>([]);
  const loadingImages = ref(false);
  const activeCategory = ref<string | undefined>(undefined);
  const activeDescription = ref<string | undefined>(undefined);

  const hasNextPage = computed(() => start.value + limit.value < total.value);
  const hasPrevPage = computed(() => start.value > 0);
  const pages = computed(() => Math.ceil(total.value / limit.value));
  const currentPage = computed(() => Math.floor(start.value / limit.value) + 1);

  async function fetchImages(category?: string, description?: string) {
    if (loadingImages.value) return;

    if (category !== undefined) {
      activeCategory.value = category;
    }
    if (description !== undefined) {
      activeDescription.value = description;
    }

    loadingImages.value = true;
    error.value = null;

    try {
      const resp = await ImagenLibraryApi.getImagesFromLibrary(
        brandId,
        limit.value,
        start.value,
        activeCategory.value,
        activeDescription.value,
      );

      images.value = resp.data;
      total.value = resp.total ?? 0;
    } catch (e) {
      console.error(e);
      error.value = "Error loading images.";
    } finally {
      loadingImages.value = false;
    }
  }

  function nextPage() {
    if (hasNextPage.value) {
      start.value += limit.value;
      fetchImages(activeCategory.value, activeDescription.value);
    }
  }

  function prevPage() {
    if (hasPrevPage.value) {
      start.value = Math.max(0, start.value - limit.value);
      fetchImages(activeCategory.value, activeDescription.value);
    }
  }

  function resetImages() {
    start.value = 0;
    total.value = 0;
    images.value = [];
  }

  return {
    selectedFile,
    loadingFromUrl,
    error,
    activeTarget,
    lastTarget,
    setActiveTarget,
    setSelectedFile,

    images,
    limit,
    start,
    total,
    pages,
    currentPage,
    loadingImages,
    hasNextPage,
    hasPrevPage,
    fetchImages,
    nextPage,
    prevPage,
    resetImages,
  };
});
