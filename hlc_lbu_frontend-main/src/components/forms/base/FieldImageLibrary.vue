<script lang="ts" setup>
import { useField, useFieldError } from "vee-validate";
import { ImageLibrarySource } from "@/components/images/library/image-library.types";

interface Props {
  name: string;
  label?: string;
  description?: string;
  accept?: string;
  required?: boolean;
  cropper?: boolean;
  previewAspectRatio?: number;
  cropperAspectRatio?: number;
  disabled?: boolean;
  previewSrc?: string;
  isSaving?: boolean;

  customSources?: ImageLibrarySource[];
}

const props = withDefaults(defineProps<Props>(), { previewAspectRatio: 1 / 1 });

const { t } = useI18n();

const { value, setValue } = useField<
  ImageLibraryFile | Blob | string | undefined
>(() => props.name);
const errorMessage = useFieldError(() => props.name);

// Handle both File objects and string URLs
const url = useObjectOrStringUrl(value);

const emit = defineEmits<{
  selected: [ImageLibraryFile];
}>();

const { isOpen: isModalOpen, open: openLibrary } = useImageLibraryModal({
  id: "FieldImageLibraryModal",
  disabled: () => props.disabled,
  onSelect: (file) => {
    setValue(file, true);
    emit("selected", file);
  },
});

const slots = useSlots();

const filteredSourceSlots = computed(() =>
  Object.fromEntries(
    Object.entries(slots).filter(([key, _value]) => key.startsWith("source:")),
  ),
);
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-2.5">
    <!-- Global Image Library Modal -->
    <ImageLibraryModal
      v-if="isModalOpen"
      v-model="isModalOpen"
      :accept="accept"
      :cropper="cropper"
      :aspectRatio="cropperAspectRatio"
      :disabled="disabled"
      :customSources="customSources"
    >
      <!-- Pass all the slots whose name start with "source:" -->
      <template
        v-for="(_, name) in filteredSourceSlots"
        :key="name"
        #[name]="scope"
      >
        <slot :name v-bind="scope ?? {}" />
      </template>
    </ImageLibraryModal>

    <FieldLabel v-if="label" :required="required">
      {{ label
      }}<template v-if="description" #description>{{ description }}</template>

      <template v-if="$slots.labelHelp" #help>
        <slot name="labelHelp" />
      </template>
    </FieldLabel>

    <!-- Retain hidden input for form compatibility, though selection comes from the library -->
    <input
      :id="name"
      :name="name"
      type="file"
      hidden
      :accept="accept ? `${accept},image/svg+xml` : 'image/*,image/svg+xml'"
      :disabled="disabled"
      tabindex="-1"
    />

    <!-- Preview and trigger -->
    <label
      class="tw:rounded-[20px] tw:bg-white tw:p-3"
      :class="{ 'tw:cursor-pointer': !disabled }"
      @click.prevent="openLibrary"
      :for="undefined"
    >
      <div
        class="tw:group tw:relative tw:flex tw:h-full tw:flex-col tw:items-center tw:justify-center tw:gap-4 tw:rounded-[5px] tw:bg-[#DFDAEA]"
        :style="{ aspectRatio: previewAspectRatio ?? cropperAspectRatio }"
      >
        <img
          v-if="url ?? previewSrc"
          :src="url ?? previewSrc"
          class="tw:h-full tw:w-full tw:rounded-[5px] tw:object-contain"
          :class="{ 'tw:brightness-40': !url && !previewSrc }"
        />

        <!-- Overlay for selection -->
        <div
          v-if="!disabled && !isSaving"
          class="tw:absolute tw:inset-0 tw:flex tw:flex-col tw:items-center tw:justify-center tw:gap-4 tw:rounded-[5px]"
          :class="{
            'tw:opacity-100': !url,
            'tw:bg-black/50 tw:opacity-0 tw:transition-opacity tw:group-hover:opacity-100':
              url,
          }"
        >
          <Icon
            icon="tabler-photo"
            class="tw:text-[38px]"
            :class="{ 'tw:text-white': url ?? previewSrc }"
          />

          <Button as="button" size="sm" type="button">
            {{ t("forms.choose-image") }}
          </Button>
        </div>

        <div
          v-if="isSaving"
          class="tw:t-0 tw:absolute tw:flex tw:h-full tw:w-full tw:items-center tw:justify-center"
        >
          <Icon
            icon="tabler-loader-2"
            class="tw:animate-spin tw:text-3xl tw:text-primary"
          />
          <span class="saving-image-text tw:ml-2 tw:text-white">
            {{ t("forms.saving-image") }}
          </span>
        </div>
      </div>
    </label>

    <FieldError v-if="errorMessage">
      {{ errorMessage }}
    </FieldError>

    <FieldHint v-if="$slots.hint">
      <slot name="hint" />
    </FieldHint>
  </div>
</template>

<style>
.saving-image-text {
  text-shadow: 0 2px 2px rgba(0, 0, 0, 1);
}
</style>
