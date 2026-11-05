<script lang="ts" setup>
import { useField, useFieldError } from "vee-validate";
import { FileFormat } from "./common-field-props";

export type FieldFilesFormatName = "png" | "jpg" | "jpeg" | "webp";

export type FieldFileFormat = FileFormat<FieldFilesFormatName>;

interface Props {
  name: string;
  label?: string;
  description?: string;
  required?: boolean;
  cropper?: boolean;
  previewAspectRatio?: number;
  cropperAspectRatio?: number;
  disabled?: boolean;
  previewSrc?: string;

  maxSize?: number;
  acceptedFormats?: FieldFilesFormatName[];
}

const props = withDefaults(defineProps<Props>(), {
  // 25 mega bytes
  maxSize: 25 * 1024 * 1024,
  acceptedFormats: () => ["png", "jpg", "jpeg", "webp"],
  previewAspectRatio: 1 / 1,
});
const { t } = useI18n();

const { value, setValue } = useField<File | string | undefined>(
  () => props.name,
  undefined,
);

const errorMessage = useFieldError(() => props.name);

// Handle both File objects and string URLs
const url = useObjectOrStringUrl(value);

const isModalOpen = ref(false);
const fileToCrop = ref<File>();
const isDragging = ref(false);
const enterTarget = ref<HTMLElement | undefined>(undefined);
const localError = ref<string | undefined>(undefined);

const allFileFormats: FieldFileFormat[] = [
  {
    name: "png",
    type: ["image/png"],
    imagePreview: true,
  },
  {
    name: "jpeg",
    type: ["image/jpeg"],
    imagePreview: true,
  },
  {
    name: "jpg",
    type: ["image/jpeg"],
    imagePreview: true,
  },
  {
    name: "webp",
    type: ["image/webp"],
    imagePreview: true,
  },
];

const validFileFormats = computed(() =>
  allFileFormats.filter((format) =>
    props.acceptedFormats.some(
      (acceptedFormat) => acceptedFormat === format.name,
    ),
  ),
);
const inputAccept = computed(() =>
  validFileFormats.value.flatMap((format) => format.type).join(","),
);

const supportedFileFormatsText = computed(() =>
  validFileFormats.value
    .map((format) => t(`forms.file-upload.formats.${format.name}`))
    .join(", "),
);

const getValidFileFormat = (file: File) => {
  const foundFileFormat = validFileFormats.value.find((format) =>
    format.type.some((type) => type === file.type),
  );

  return foundFileFormat;
};

const processFile = (file: File) => {
  // Check file size
  if (file.size > props.maxSize) {
    localError.value = t("forms.file-upload.file-size-error", {
      maxSize: formatFileSize(props.maxSize),
    });
    return;
  }

  // Check file format
  const foundFileFormat = getValidFileFormat(file);
  if (!foundFileFormat) {
    localError.value = t("forms.file-upload.file-format-error", {
      formats: supportedFileFormatsText.value,
    });
    return;
  }

  // Clear any previous error and accept the file
  localError.value = undefined;

  if (props.cropper) {
    isModalOpen.value = true;
    fileToCrop.value = file;
  } else {
    setValue(file, true);
  }
};

const handleClick = (e: Event) => {
  const target = e.target as HTMLInputElement;
  // This allows uploading the same file again
  target.value = "";
};

const handleChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  processFile(file);
};

const handleDragEnter = (e: DragEvent) => {
  if (props.disabled) return;
  e.preventDefault();

  // Store the target to check against on drag leave
  enterTarget.value = e.target as HTMLElement;
  isDragging.value = true;

  // Reset any previous drop-format error when user starts dragging a file in
  localError.value = undefined;
};

const handleDragOver = (e: DragEvent) => {
  if (props.disabled) return;
  e.preventDefault();
};

const handleDragLeave = (e: DragEvent) => {
  // Check target to avoid flickering when dragging over child elements
  if (props.disabled || e.target !== enterTarget.value) return;

  isDragging.value = false;
};

const handleDrop = (e: DragEvent) => {
  if (props.disabled) return;
  e.preventDefault();

  enterTarget.value = undefined;
  isDragging.value = false;

  // Extract first file
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  processFile(file);
};

const handleSaveCrop = (image: File) => {
  setValue(image, true);
};

const handleDelete = () => {
  setValue(undefined, true);
};
</script>

<template>
  <div class="tw:flex tw:flex-col" :class="{ 'tw:opacity-50': disabled }">
    <!-- Modal to crop image -->
    <ModalImageCropper
      v-if="cropper && fileToCrop"
      :imageFile="fileToCrop"
      v-model="isModalOpen"
      @save="handleSaveCrop"
      :aspectRatio="cropperAspectRatio"
    />

    <FieldLabel v-if="label" :for="name" :required="required">
      {{ label
      }}<template v-if="description" #description>{{ description }}</template>

      <template v-if="$slots.labelHelp" #help>
        <slot name="labelHelp" />
      </template>
    </FieldLabel>

    <!-- Hidden input to trigger the file upload -->
    <input
      :id="name"
      :name="name"
      type="file"
      hidden
      @change="handleChange"
      @click="handleClick"
      :accept="inputAccept"
      :disabled="disabled"
    />

    <!-- Visible drop area for the image -->
    <label
      class="tw:group tw:relative tw:overflow-hidden tw:rounded-2xl tw:border-2 tw:bg-white"
      :class="{
        'tw:cursor-pointer': !disabled,
        'tw:hover:border-primary': !value,
        'tw:border-dashed': !value || isDragging,
        'tw:border-primary tw:opacity-80': isDragging,
      }"
      :style="{ aspectRatio: previewAspectRatio ?? cropperAspectRatio }"
      :for="name"
      @dragenter.prevent="handleDragEnter"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <!-- Image preview -->
      <img
        v-if="url ?? previewSrc"
        :src="url ?? previewSrc"
        class="tw:h-full tw:w-full tw:rounded-[5px] tw:object-contain"
        :class="{ 'tw:brightness-40': !url && !previewSrc }"
      />

      <!-- Overlay for uploaded image on hover -->
      <div
        v-if="!disabled"
        class="tw:absolute tw:inset-0 tw:flex tw:flex-col tw:items-center tw:justify-center tw:rounded-[5px]"
        :class="{
          'tw:bg-black/70 tw:text-white tw:opacity-0 tw:transition-opacity tw:group-hover:opacity-100':
            url ?? previewSrc,
        }"
      >
        <Icon icon="mynaui:cloud-upload" class="tw:text-[24px]" />

        <p class="tw:mt-4 tw:text-sm tw:font-semibold">
          <slot name="inputTitle">{{ $t("forms.file-upload.upload") }}</slot>
        </p>

        <p class="tw:mt-1 tw:text-sm">
          {{
            $t("forms.file-upload.upload-description", {
              formats: supportedFileFormatsText,
              maxSize: formatFileSize(maxSize),
            })
          }}
        </p>

        <Button
          as="label"
          size="sm"
          type="button"
          :for="name"
          class="tw:mt-8"
          color="secondary"
          variant="outlined"
        >
          {{ $t("global.browse") }}
        </Button>
      </div>

      <!-- Delete button -->
      <button
        v-if="value"
        type="button"
        class="tw:absolute tw:top-0 tw:right-0 tw:m-2 tw:rounded-full tw:bg-gray-200 tw:p-2 tw:hover:brightness-95"
        @mousedown="handleDelete"
      >
        <Icon icon="custom-trash" class="tw:text-[24px]" />
      </button>
    </label>

    <FieldError v-if="errorMessage || localError">
      {{ errorMessage || localError }}
    </FieldError>

    <FieldHint v-if="$slots.hint">
      <slot name="hint" />
    </FieldHint>
  </div>
</template>
