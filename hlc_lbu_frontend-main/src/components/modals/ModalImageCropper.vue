<script lang="ts" setup>
import { Cropper, RectangleStencil } from "vue-advanced-cropper";
import type { ImageSize, VisibleArea } from "vue-advanced-cropper";
import "vue-advanced-cropper/dist/style.css";
import Modal from "@/components/modals/base/Modal.vue";

export interface ModalImageCropperProps {
  imageFile: File;
  aspectRatio?: number;
  maxWidth?: number | string;
  dismissible?: boolean;
}

const props = withDefaults(defineProps<ModalImageCropperProps>(), {
  dismissible: true,
});

const emit = defineEmits<{
  save: [image: File];
}>();

const isOpen = defineModel<boolean>({ required: true });
const isLoading = ref(false);
const url = useObjectUrl(() => props.imageFile);

const cropper = ref<InstanceType<typeof Cropper>>();

function getDefaultCropSize({
  imageSize,
  visibleArea,
}: {
  imageSize: ImageSize;
  visibleArea?: VisibleArea | null;
}) {
  const area = visibleArea || imageSize;
  return {
    width: area.width,
    height: area.height,
  };
}

const handleSave = () => {
  const result = cropper.value?.getResult();
  if (result && result.canvas) {
    isLoading.value = true;
    const canvas = result.canvas as HTMLCanvasElement;

    const originalName = props.imageFile?.name ?? "image";
    const originalType = props.imageFile?.type || "image/png";
    const preferredType =
      originalType === "image/svg+xml" ? "image/png" : originalType;

    const finish = (blob: Blob | null) => {
      try {
        const usedBlob = blob ?? new Blob([], { type: preferredType });
        if (!blob) {
          const dataUrl = canvas.toDataURL(preferredType);
          const arr = dataUrl.split(",");
          const mime = arr[0].match(/:(.*?);/)?.[1] || preferredType;
          const bstr = atob(arr[1] || "");
          let n = bstr.length;
          const u8arr = new Uint8Array(n);
          while (n--) u8arr[n] = bstr.charCodeAt(n);
          const fallbackBlob = new Blob([u8arr], { type: mime });
          const name = uniqueCroppedName(
            ensureImageExtension(originalName, mime),
          );
          const file = new File([fallbackBlob], name, { type: mime });
          emit("save", file);
        } else {
          const name = uniqueCroppedName(
            ensureImageExtension(originalName, usedBlob.type),
          );
          const file = new File([usedBlob], name, { type: usedBlob.type });
          emit("save", file);
        }
      } finally {
        isOpen.value = false;
        isLoading.value = false;
      }
    };

    canvas.toBlob((blob) => {
      if (blob) return finish(blob);
      canvas.toBlob((blobPng) => finish(blobPng), "image/png");
    }, preferredType);
  } else {
    isLoading.value = false;
    isOpen.value = false;
  }
};

function ensureImageExtension(name: string, mime: string): string {
  const lower = name.toLowerCase();
  const hasKnownExt = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"].some(
    (ext) => lower.endsWith(ext),
  );
  if (hasKnownExt) {
    if (mime === "image/png" && !lower.endsWith(".png"))
      return swapExt(name, "png");
    if (
      mime === "image/jpeg" &&
      !(lower.endsWith(".jpg") || lower.endsWith(".jpeg"))
    )
      return swapExt(name, "jpg");
    if (mime === "image/webp" && !lower.endsWith(".webp"))
      return swapExt(name, "webp");
    if (mime === "image/gif" && !lower.endsWith(".gif"))
      return swapExt(name, "gif");
    if (mime === "image/svg+xml" && !lower.endsWith(".svg"))
      return swapExt(name, "svg");
    return name;
  }
  switch (mime) {
    case "image/png":
      return name + ".png";
    case "image/jpeg":
      return name + ".jpg";
    case "image/webp":
      return name + ".webp";
    case "image/gif":
      return name + ".gif";
    case "image/svg+xml":
      return name + ".svg";
    default:
      return name;
  }
}

function swapExt(name: string, ext: string) {
  const i = name.lastIndexOf(".");
  return (i >= 0 ? name.slice(0, i) : name) + `.${ext}`;
}
function uniqueCroppedName(basename: string) {
  const dot = basename.lastIndexOf(".");
  const stamp = Date.now();
  const rand = Math.random().toString(36).slice(2, 6);
  if (dot > 0) {
    const name = basename.slice(0, dot);
    const ext = basename.slice(dot);
    return `${name}-crop-${stamp}-${rand}${ext}`;
  }
  return `${basename}-crop-${stamp}-${rand}`;
}
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="760"
    :radius="20"
    :closeButton="props.dismissible"
    :closeOnClickOutside="props.dismissible"
    class="tw:p-6 tw:pt-16"
  >
    <div class="tw:flex tw:h-full tw:flex-col tw:gap-6" @click.stop>
      <div class="tw:w-full tw:flex-1">
        <div class="tw:h-[50vh] tw:w-full tw:md:h-[55vh]">
          <Cropper
            ref="cropper"
            class="image-cropper tw:h-full tw:w-full"
            :src="url"
            :stencil-component="RectangleStencil"
            :stencil-props="{ aspectRatio }"
            image-restriction="fit-area"
            :default-size="getDefaultCropSize"
          />
        </div>
      </div>
      <div class="tw:relative">
        <button
          type="button"
          class="tw:w-full tw:rounded-md tw:bg-primary tw:px-4 tw:py-3 tw:font-semibold tw:text-white tw:hover:bg-primary/90 tw:disabled:opacity-60"
          :disabled="isLoading"
          @click.stop="handleSave"
        >
          <span v-if="!isLoading">{{ $t("global.save") }}</span>
          <span v-else>{{ $t("global.saving") }}</span>
        </button>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
@reference "#styles/main.css";

.image-cropper :deep(.vue-simple-handler) {
  @apply tw:border tw:border-gray-500 tw:bg-gray-100! tw:shadow;
}
</style>
