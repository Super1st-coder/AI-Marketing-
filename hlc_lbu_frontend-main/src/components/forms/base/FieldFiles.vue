<script lang="ts">
import { FieldBasicProps, FileFormat } from "./common-field-props";

/**
 * What `FieldFiles` needs of a file that's already saved. Whatever else
 * identifies it (an id, a storage key) is added by the form through the
 * component's generic.
 */
export type FieldFilesBackendFile = {
  name: string;
  /** In bytes. Shown under the name when known. */
  size?: number;
};

export type DeleteBackendFileConfirmFn<
  T extends FieldFilesBackendFile = FieldFilesBackendFile,
> = (file: T) => Promise<boolean>;

export type FieldFilesFormatName =
  "pdf" | "xls" | "png" | "jpg" | "jpeg" | "webp" | "mp4" | "mov";

export type FieldFileFormat = FileFormat<FieldFilesFormatName>;

/** Every format `FieldFiles` knows, with its mime types and how it previews. */
export const FIELD_FILES_FORMATS: FieldFileFormat[] = [
  {
    name: "pdf",
    type: ["application/pdf"],
    icon: "tabler:file-type-pdf",
  },
  {
    name: "xls",
    type: [
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
    icon: "tabler:file-type-xls",
  },
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
  {
    name: "mp4",
    type: ["video/mp4"],
    icon: "tabler:video",
    videoPreview: true,
  },
  {
    name: "mov",
    type: ["video/quicktime"],
    icon: "tabler:video",
    videoPreview: true,
  },
];

/** The formats of the given names, in `FIELD_FILES_FORMATS`' order. */
export function getFieldFilesFormats(names: FieldFilesFormatName[]) {
  return FIELD_FILES_FORMATS.filter((format) => names.includes(format.name));
}

/** The mime types of the given formats, for an input's `accept`. */
export function getFieldFilesMimeTypes(names: FieldFilesFormatName[]) {
  return getFieldFilesFormats(names).flatMap((format) => format.type);
}

export type FieldFilesProps<
  T extends FieldFilesBackendFile = FieldFilesBackendFile,
> = FieldBasicProps & {
  dropAreaLabel?: string;
  inputDescription?: string;
  maxSize?: number;
  /** Most files the field can hold. No limit by default. */
  maxFiles?: number;
  size?: "sm" | "lg";
  /** `horizontal` puts the icon, the text and the browse button in a row. */
  orientation?: "vertical" | "horizontal";
  /** Adds a Browse button to the drop area. */
  browseButton?: boolean;
  acceptedFormats?: FieldFilesFormatName[];
  /**
   * Asks before removing a saved file, and does whatever removing it needs.
   * Without it a saved file is removed from the value like a picked one, so
   * the form's save handles it.
   */
  deleteBackendFileConfirmFn?: DeleteBackendFileConfirmFn<T>;
  /** A link to preview a saved image or video. */
  getBackendFileSrc?: (file: T) => string | undefined;
} & {
  name: string;
};
</script>

<script
  lang="ts"
  setup
  generic="T extends FieldFilesBackendFile = FieldFilesBackendFile"
>
import { useField } from "vee-validate";
import { ref } from "vue";

const props = withDefaults(defineProps<FieldFilesProps<T>>(), {
  // 25 mega bytes
  maxSize: 25 * 1024 * 1024,
  size: "lg",
  orientation: "vertical",
  acceptedFormats: () => ["pdf", "xls"],
});

const { t } = useI18n();

const { value, setValue, errorMessage } = useField<(File | T)[] | undefined>(
  () => props.name,
  undefined,
);
const fileInput = ref<HTMLInputElement>();
const localError = ref<string>();
const showDeleteConfirmModal = ref(false);
const backendFileIndexToDelete = ref(0);

const backendFileToDelete = computed<T | undefined>(() => {
  const file = value.value?.[backendFileIndexToDelete.value];
  return file === undefined || isFile(file) ? undefined : file;
});

const validFileFormats = computed(() =>
  getFieldFilesFormats(props.acceptedFormats),
);
const inputAccept = computed(() =>
  getFieldFilesMimeTypes(props.acceptedFormats).join(","),
);

const supportedFileFormatsText = computed(() =>
  validFileFormats.value
    .map((format) => t(`forms.file-upload.formats.${format.name}`))
    .join(", "),
);

function isFile(file: File | T): file is File {
  return file instanceof File;
}

const getValidFileFormat = (file: File | T) => {
  if (isFile(file)) {
    // Find the file format using the mime type
    const foundFileFormat = validFileFormats.value.find((format) =>
      format.type.some((type) => type === file.type),
    );

    return foundFileFormat;
  } else {
    // Get the extension from the file name
    const extension = file.name.includes(".")
      ? file.name.split(".").pop()?.toLowerCase()
      : undefined;

    if (extension) {
      // Find the file format using the extension
      const foundFileFormat = validFileFormats.value.find(
        (format) => format.name === extension,
      );

      return foundFileFormat;
    }
  }

  return undefined;
};

const getFileIcon = (file: File | T) => {
  const format = getValidFileFormat(file);
  return format?.icon ?? "tabler:file";
};

// A picked file previews itself. A saved one needs a link from the parent
function getPreviewSrc(file: File | T) {
  return isFile(file) ? file : props.getBackendFileSrc?.(file);
}

function hasImagePreview(file: File | T) {
  return Boolean(getValidFileFormat(file)?.imagePreview && getPreviewSrc(file));
}

// The thumbnail shows while the saved file's link loads
function hasVideoPreview(file: File | T) {
  return Boolean(
    getValidFileFormat(file)?.videoPreview &&
    (isFile(file) || props.getBackendFileSrc),
  );
}

const processFileList = (files: FileList) => {
  const selectedFiles = Array.from(files);

  // Check file count
  if (
    props.maxFiles !== undefined &&
    (value.value?.length ?? 0) + selectedFiles.length > props.maxFiles
  ) {
    localError.value = t(
      "forms.file-upload.max-files-error",
      { count: props.maxFiles },
      props.maxFiles,
    );
    return;
  }

  for (let file of selectedFiles) {
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
  }

  // Update value
  const existingFiles = value.value || [];
  setValue([...existingFiles, ...selectedFiles], true);
  localError.value = undefined;
};

const handleChange = (event: Event) => {
  // Process uploaded files
  const input = event.target as HTMLInputElement;
  if (!input.files) return;
  processFileList(input.files);
};

// The value is what's kept, not the input: the input unmounts with the drop
// area once a single file is picked
const removeFile = (index: number) => {
  const files = [...(value.value ?? [])];
  files.splice(index, 1);
  setValue(files, true);
};

function handleDeleteFile(index: number) {
  const targetFile = value.value?.[index];
  if (!targetFile) {
    return;
  }

  if (isFile(targetFile) || !props.deleteBackendFileConfirmFn) {
    removeFile(index);
  } else {
    backendFileIndexToDelete.value = index;
    showDeleteConfirmModal.value = true;
  }
}

async function handleConfirmBackendDelete() {
  if (!props.deleteBackendFileConfirmFn || !backendFileToDelete.value) {
    return;
  }

  await props.deleteBackendFileConfirmFn(backendFileToDelete.value);
  removeFile(backendFileIndexToDelete.value);
}

const isFull = computed(
  () =>
    props.maxFiles !== undefined &&
    (value.value?.length ?? 0) >= props.maxFiles,
);

// Each description on its own line, unless horizontal
const descriptionClass = computed(() =>
  props.orientation === "vertical" ? "tw:block" : undefined,
);

// A field for one file shows the file instead of the drop area
const showDropArea = computed(() => !(props.maxFiles === 1 && isFull.value));

const isDragging = ref(false);
const enterTarget = ref<HTMLElement | undefined>(undefined);

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

  // Process dropped files
  const files = e.dataTransfer?.files;
  if (!files) return;
  processFileList(files);
};

// Update the input files when value changes
watch(value, (newFiles) => {
  if (fileInput.value && newFiles) {
    const dataTransfer = new DataTransfer();
    newFiles.filter(isFile).forEach((file) => dataTransfer.items.add(file));
    fileInput.value.files = dataTransfer.files;
  }
});
</script>

<template>
  <div
    :class="{
      'tw:pointer-events-none': disabled,
    }"
  >
    <!-- Label -->
    <FieldLabel v-if="props.label" :required="required" :for="name">
      {{ label
      }}<template v-if="description" #description>{{ description }}</template>

      <template v-if="$slots.labelHelp" #help>
        <slot name="labelHelp" />
      </template>
    </FieldLabel>

    <!-- Drop area -->
    <label
      v-if="showDropArea"
      class="tw:block tw:w-full tw:rounded-2xl tw:border tw:border-dashed tw:bg-white"
      :class="{
        'tw:px-4 tw:py-6': orientation === 'vertical',
        'tw:p-4': orientation === 'horizontal',
        'tw:border-gray-300': !isDragging,
        'tw:border-primary': isDragging,
        'tw:cursor-pointer': !isFull,
        'tw:cursor-not-allowed': isFull,
        'tw:opacity-50': disabled || isFull,
      }"
      @dragenter.prevent="handleDragEnter"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div
        class="tw:flex tw:gap-4"
        :class="{
          'tw:mx-auto tw:flex-col tw:items-center': orientation === 'vertical',
          'tw:items-center': orientation === 'horizontal',
          'tw:max-w-[320px]': orientation === 'vertical' && size === 'sm',
          'tw:max-w-[420px]': orientation === 'vertical' && size === 'lg',
        }"
      >
        <Icon
          icon="tabler:upload"
          class="tw:shrink-0 tw:text-2xl"
          :class="{ 'tw:text-secondary-text': orientation === 'vertical' }"
        />

        <div
          :class="{
            'tw:text-center': orientation === 'vertical',
            'tw:grow': orientation === 'horizontal',
          }"
        >
          <p
            class="tw:mb-1"
            :class="{
              'tw:text-sm tw:font-semibold':
                orientation === 'vertical' && size === 'sm',
              'tw:font-extrabold': orientation === 'vertical' && size === 'lg',
              'tw:font-semibold': orientation === 'horizontal',
            }"
          >
            {{ props.dropAreaLabel || "" }}
          </p>

          <!-- One line per description, or a single paragraph when
            horizontal. The spaces are explicit, since the template drops the
            ones between tags -->
          <p class="tw:text-sm tw:text-gray-500">
            <!-- Goes before the supported formats and the maximum size -->
            <template v-if="$slots.dropAreaDescription">
              <span :class="descriptionClass">
                <slot name="dropAreaDescription" />
              </span>
              {{ " " }}
            </template>

            <span :class="descriptionClass">
              {{
                $t("forms.file-upload.supported-formats", {
                  formats: supportedFileFormatsText,
                })
              }}
            </span>
            {{ " " }}
            <span :class="descriptionClass">
              {{
                $t("forms.file-upload.maximum-file-size", {
                  maxSize: formatFileSize(maxSize),
                })
              }}
            </span>

            <!-- A single file needs no limit: the drop area hides once it's in -->
            <template v-if="maxFiles !== undefined && maxFiles > 1">
              {{ " " }}
              <span :class="descriptionClass">
                {{
                  $t(
                    "forms.file-upload.maximum-files",
                    { count: maxFiles },
                    maxFiles,
                  )
                }}
              </span>
            </template>
          </p>
        </div>

        <!-- A button inside the label doesn't open the picker by itself -->
        <Button
          v-if="browseButton"
          color="secondary"
          variant="outlined"
          size="sm"
          type="button"
          class="tw:shrink-0"
          :uppercase="false"
          :disabled="disabled || isFull"
          @click.prevent="fileInput?.click()"
        >
          {{ $t("global.browse") }}
        </Button>

        <input
          :name="name"
          :accept="inputAccept"
          type="file"
          multiple
          @change="handleChange"
          ref="fileInput"
          v-show="false"
          hidden
          :disabled="disabled || isFull"
        />
      </div>
    </label>

    <!-- Error -->
    <FieldError v-if="error || errorMessage || localError">
      {{ error || errorMessage || localError }}
    </FieldError>

    <!-- Hint -->
    <FieldHint v-if="$slots.hint">
      <slot name="hint" />
    </FieldHint>

    <!-- Uploaded files -->
    <div
      v-if="value && value.length > 0"
      class="tw:flex tw:flex-col tw:gap-2"
      :class="{
        'tw:mt-5': showDropArea,
        'tw:opacity-50': disabled,
      }"
    >
      <div
        v-for="(file, index) in value"
        :key="index"
        class="tw:flex tw:items-start tw:gap-3"
      >
        <!-- Icon -->
        <div
          class="tw:h-11 tw:max-w-16 tw:shrink-0 tw:grow tw:rounded-lg tw:bg-gray-200"
        >
          <VideoFilePlayButton
            v-if="hasVideoPreview(file)"
            :src="getPreviewSrc(file)"
            :label="$t('forms.file-upload.play-video', { name: file.name })"
            class="tw:pointer-events-auto tw:h-full tw:w-full"
          />
          <ImgFile
            v-else-if="hasImagePreview(file)"
            :src="getPreviewSrc(file)"
            class="tw:h-full tw:w-full tw:rounded-lg tw:object-cover"
          />
          <Icon
            v-else
            :icon="getFileIcon(file)"
            class="tw:h-full tw:w-full tw:shrink-0 tw:text-3xl tw:text-success"
          />
        </div>

        <!-- Header-->
        <div class="tw:flex tw:min-w-0 tw:grow tw:flex-col tw:gap-1 tw:text-sm">
          <!-- File name -->
          <p class="tw:truncate tw:font-semibold" :title="file.name">
            {{ file.name }}
          </p>

          <!-- File size -->
          <p v-if="file.size !== undefined" class="tw:text-gray-500">
            {{ formatFileSize(file.size) }}
          </p>
        </div>

        <!-- Remove button -->
        <button
          @click="handleDeleteFile(index)"
          class="tw:p-0.5"
          type="button"
          :aria-label="$t('forms.file-upload.remove-file', { name: file.name })"
        >
          <Icon icon="tabler:x" class="tw:shrink-0 tw:text-2xl" />
        </button>
      </div>
    </div>

    <!-- Delete confirmation -->
    <ModalDelete
      v-if="deleteBackendFileConfirmFn !== undefined && backendFileToDelete"
      v-model="showDeleteConfirmModal"
      :confirmFn="handleConfirmBackendDelete"
    >
      <template #title>
        <slot name="deleteConfirmTitle" :file="backendFileToDelete">
          {{
            $t("forms.file-upload.delete-confirm-title", {
              file: backendFileToDelete.name,
            })
          }}
        </slot>
      </template>

      <template #description>
        <slot name="deleteConfirmDescription" :file="backendFileToDelete">
          {{
            $t("forms.file-upload.delete-confirm-description", {
              file: backendFileToDelete.name,
            })
          }}
        </slot>
      </template>

      <template #warning>
        <slot name="deleteConfirmWarning" :file="backendFileToDelete" />
      </template>
    </ModalDelete>
  </div>
</template>
