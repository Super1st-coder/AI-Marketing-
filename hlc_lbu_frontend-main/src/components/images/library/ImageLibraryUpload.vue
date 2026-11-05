<script setup lang="ts">
import { useImageLibraryStore } from "@/stores/ImageLibraryStore";
import { object, string } from "yup";

interface Props {
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "image-selected", payload: { file: File; src: string }): void;
  (e: "error", payload: { message: string }): void;
}>();

const isDragging = ref(false);
const inputEl = ref<HTMLInputElement | null>(null);
const pendingFile = ref<File | undefined>();
const isModalOpen = ref(false);
const customName = ref("");
const previewUrl = useObjectUrl(pendingFile);
const customNameErrorMessage = ref("");
const { t } = useI18n();

const imageSchema = computed(() =>
  object({
    customName: string()
      .trim()
      .required(t("image-library.common.image-name-required")),
  }),
);

function openPicker() {
  if (props.disabled || pendingFile.value) return;

  inputEl.value?.click();
}

function changeImage() {
  inputEl.value?.click();
}

function onDragOver(e: DragEvent) {
  e.preventDefault();
  if (props.disabled) return;
  isDragging.value = true;
}

function onDragLeave() {
  isDragging.value = false;
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  if (props.disabled || pendingFile.value) return;

  isDragging.value = false;

  const file = e.dataTransfer?.files?.[0];
  if (!file) return;

  if (!isAccepted(file)) {
    emit("error", { message: t("image-library.upload.invalid-file-type") });
    return;
  }

  handleSelectedFile(file);
}

function onInputChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  if (!isAccepted(file)) {
    emit("error", { message: t("image-library.upload.invalid-file-type") });
    target.value = "";
    return;
  }

  handleSelectedFile(file);
  target.value = "";
}

function isAccepted(file: File) {
  const accept = props.accept?.split(",").map((s) => s.trim().toLowerCase());
  if (!accept || accept.length === 0) {
    return (
      file.type.startsWith("image/") || file.name.toLowerCase().endsWith(".svg")
    );
  }

  const fileType = file.type.toLowerCase();
  const fileName = file.name.toLowerCase();
  return accept.some((rule) => {
    if (rule === "image/*") return fileType.startsWith("image/");
    if (rule === "image/svg+xml")
      return fileType === "image/svg+xml" || fileName.endsWith(".svg");
    if (rule.startsWith(".")) return fileName.endsWith(rule);
    return fileType === rule;
  });
}

function handleSelectedFile(file: File) {
  pendingFile.value = file;
  customName.value = file.name.replace(/\.[^/.]+$/, "");
  if (props.cropper) {
    nextTick(() => (isModalOpen.value = true));
  }
}

function handleSaveCrop(cropped: File) {
  const dot = cropped.name.lastIndexOf(".");
  const ext = dot >= 0 ? cropped.name.slice(dot) : "";
  const name = customName.value?.trim() || cropped.name.slice(0, dot);
  const renamed = new File([cropped], `${name}${ext}`, { type: cropped.type });

  pendingFile.value = renamed;
  isModalOpen.value = false;
}

async function confirmSelection() {
  const file = pendingFile.value;
  if (!file) return;

  try {
    await imageSchema.value.validate({ customName: customName.value });
    customNameErrorMessage.value = "";
  } catch (err: any) {
    customNameErrorMessage.value = err.message;
    return;
  }

  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot) : "";
  const name = customName.value?.trim() || file.name.slice(0, dot);

  const renamed = new File([file], `${name}${ext}`, { type: file.type });
  const src = previewUrl.value || URL.createObjectURL(renamed);

  const store = useImageLibraryStore();
  store.setSelectedFile(renamed, { cropped: true, source: "upload" });
  emit("image-selected", { file: renamed, src });
}

function clearSelection() {
  pendingFile.value = undefined;
  customName.value = "";
}

watch(customName, () => {
  if (customNameErrorMessage.value) customNameErrorMessage.value = "";
});
</script>

<template>
  <div>
    <ImageLibraryTitle icon="tabler:download">
      {{ $t("image-library.sources.upload") }}
    </ImageLibraryTitle>

    <Separator />

    <ModalImageCropper
      v-if="cropper && pendingFile"
      v-model="isModalOpen"
      :imageFile="pendingFile"
      :aspectRatio="aspectRatio"
      @save="handleSaveCrop"
    />

    <input
      ref="inputEl"
      type="file"
      hidden
      :disabled="disabled"
      :accept="accept ? `${accept},image/svg+xml` : 'image/*,image/svg+xml'"
      @change="onInputChange"
    />

    <div class="tw:p-6">
      <div
        class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:rounded-md tw:border tw:border-dashed tw:px-4 tw:py-10"
        :class="[
          isDragging
            ? 'tw:border-primary tw:bg-primary/5'
            : 'tw:border-secondary/30',
          disabled ? 'tw:cursor-not-allowed tw:opacity-60' : '',
          props.disabled || pendingFile ? '' : 'tw:cursor-pointer',
        ]"
        @dragover="onDragOver"
        @dragenter.prevent="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="openPicker()"
      >
        <template v-if="pendingFile && previewUrl">
          <div class="tw:mb-2 tw:w-full tw:max-w-[420px]">
            <FieldText
              v-model="customName"
              name="custom_name"
              :label="$t('image-library.common.image-name')"
              :placeholder="$t('image-library.common.enter-image-name')"
              required
            />
            <p
              v-if="customNameErrorMessage"
              class="tw:mt-1 tw:text-sm tw:text-error"
            >
              {{ customNameErrorMessage }}
            </p>
          </div>

          <div
            class="tw:w-full tw:max-w-[420px] tw:overflow-hidden tw:rounded-lg tw:border tw:border-secondary/20"
          >
            <img
              :src="previewUrl"
              :alt="$t('image-library.upload.selected-preview-alt')"
              class="tw:h-auto tw:w-full tw:object-cover"
            />
          </div>

          <div class="tw:text-center tw:text-sm tw:text-secondary">
            <strong>{{ pendingFile.name }}</strong>
            <span class="tw:ml-1">
              ({{ Math.ceil(pendingFile.size / 1024) }} KB)
            </span>
          </div>

          <div class="tw:mt-1 tw:flex tw:flex-wrap tw:justify-center tw:gap-2">
            <Button size="md" @click.stop="confirmSelection">
              {{ $t("image-library.common.use-this-image") }}
            </Button>
            <Button
              size="md"
              variant="outlined"
              color="secondary"
              @click.stop="changeImage"
            >
              {{ $t("image-library.common.change-image") }}
            </Button>
            <Button
              size="md"
              variant="text"
              color="secondary"
              @click.stop="clearSelection"
            >
              {{ $t("image-library.common.clear") }}
            </Button>
          </div>
        </template>

        <template v-else>
          <div class="tw:mb-1 tw:rounded-md tw:bg-secondary/10 tw:p-2">
            <Icon icon="tabler-upload" class="tw:text-xl tw:text-secondary" />
          </div>
          <p class="tw:text-xl">
            {{ $t("image-library.upload.drag-drop-your-image-here") }}
          </p>
          <p>{{ $t("image-library.upload.or") }}</p>
          <Button size="md" :disabled="disabled" @click.stop="openPicker">
            {{ $t("image-library.common.upload-image") }}
          </Button>
        </template>
      </div>
    </div>
  </div>
</template>
