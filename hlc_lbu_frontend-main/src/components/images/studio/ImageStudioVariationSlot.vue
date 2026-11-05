<script setup lang="ts">
import { ImageStudioVariationImage } from "./types";
import { downloadStudioImage } from "./utils";

const props = defineProps<{
  label?: string;
  previewImage?: string;
  image?: ImageStudioVariationImage;
  isGenerating?: boolean;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  add: [];
  delete: [];
  edit: [];
}>();

const { t } = useI18n();

const translatedLabel = computed(() =>
  props.label ? t(`buyer-person.image.variations.${props.label}.title`) : "",
);

async function handleDownloadImage() {
  if (!props.image) {
    return;
  }

  await downloadStudioImage(props.image);
}
</script>

<template>
  <ImageStudioLoadingCard v-if="isGenerating" />
  <!-- With image -->
  <div
    v-else-if="image"
    class="tw:group tw:relative tw:aspect-square tw:overflow-hidden tw:rounded-[10px] tw:bg-gray-500"
  >
    <!-- Image -->
    <ImgFile
      :src="image.image_blob ?? image.image_url"
      class="tw:select- transition tw:h-full tw:w-full tw:object-contain tw:group-hover:brightness-40"
    />

    <!-- Label chip -->
    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:flex tw:flex-col tw:justify-between tw:p-3"
    >
      <!-- Header -->
      <div
        class="tw:flex"
        :class="{
          'tw:justify-between': label,
          'tw:justify-end': !label,
        }"
      >
        <span
          v-if="label"
          class="tw:rounded-full tw:bg-primary-100 tw:px-2 tw:py-[3px] tw:text-xs tw:font-medium tw:text-gray-500"
        >
          {{ translatedLabel }}
        </span>

        <div
          class="tw:flex tw:justify-end tw:gap-4 tw:text-white tw:opacity-0 tw:transition tw:group-hover:opacity-100"
        >
          <!-- Download button -->
          <button
            type="button"
            class="tw:pointer-events-auto"
            @click="handleDownloadImage"
          >
            <Icon icon="tabler:download" class="tw:text-[20px]" />
          </button>

          <!-- Delete button -->
          <button
            v-if="!readOnly"
            type="button"
            class="tw:pointer-events-auto"
            @click="emit('delete')"
          >
            <Icon icon="tabler:trash" class="tw:text-[20px]" />
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div
        v-if="!readOnly"
        class="tw:flex tw:self-end tw:opacity-0 tw:transition tw:group-hover:opacity-100"
      >
        <!-- Edit button -->
        <Button
          type="button"
          icon="tabler:pencil"
          size="sm"
          variant="outlined"
          color="secondary"
          class="tw:pointer-events-auto"
          @click="emit('edit')"
        />
      </div>
    </div>
  </div>
  <!-- Without image -->
  <button
    v-else-if="!readOnly"
    type="button"
    class="tw:group tw:relative tw:aspect-square tw:overflow-hidden tw:rounded-[10px] tw:border tw:border-gray-300 tw:bg-gray-200"
    @click="emit('add')"
  >
    <!-- Preview -->
    <img
      :src="previewImage"
      class="tw:opacity-10 tw:blur-sm tw:grayscale tw:transition-all tw:select-none tw:group-hover:opacity-30 tw:group-hover:blur-none tw:group-hover:grayscale-0"
    />

    <!-- Text -->
    <div
      class="tw:absolute tw:inset-0 tw:flex tw:items-center tw:justify-center tw:text-gray-600"
    >
      <Icon icon="tabler:plus" class="tw:mr-2 tw:text-[20px]" />
      <span class="tw:font-medium">
        <template v-if="label">
          {{ translatedLabel }}
        </template>
        <template v-else>
          {{ $t("buyer-person.image.variation-add-modal.add-variation") }}
        </template>
      </span>
    </div>

    <!-- Chip -->
    <div
      v-if="label"
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:flex tw:items-start tw:p-3"
    >
      <span
        class="tw:rounded-full tw:bg-gray-100 tw:px-2 tw:py-[3px] tw:text-xs tw:font-medium tw:text-gray-500"
      >
        {{ $t("buyer-person.image.variation-add-modal.required") }}
      </span>
    </div>
  </button>
</template>
