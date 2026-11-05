<script setup lang="ts">
import { ImageStudioGeneratedImage } from "./types";
import { downloadStudioImage } from "./utils";

const props = defineProps<{
  image: ImageStudioGeneratedImage;
  disabled?: boolean;
  readOnly?: boolean;
  enableEditing?: boolean;
  enableMoreLikeThis?: boolean;
}>();
const emit = defineEmits<{
  moreLikeThis: [];
  edit: [];
  delete: [];
  preview: [];
}>();

const isLoadingImage = computed(() =>
  props.image.fetchBlob ? !props.image.image_blob : false,
);

const selectedImage = defineModel<ImageStudioGeneratedImage | undefined>(
  "selectedImage",
  {
    required: true,
  },
);

const isSelected = computed(() => selectedImage.value === props.image);
const isAnyImageSelected = computed(() => selectedImage.value !== undefined);

function handleDownloadImage() {
  downloadStudioImage(props.image);
}

function handlePreview() {
  if (!isAnyImageSelected.value || isSelected.value) {
    emit("preview");
  }
}
</script>

<template>
  <ImageStudioLoadingCard v-if="isLoadingImage" />
  <div
    v-else
    class="tw:group tw:relative tw:aspect-square tw:overflow-hidden tw:rounded-[12px] tw:bg-gray-500"
    :class="{
      'tw:ring tw:ring-primary-500': isSelected,
    }"
  >
    <ImgFile
      :src="image.image_blob ?? image.image_url"
      class="tw:h-full tw:w-full tw:object-contain tw:select-none"
      :class="{
        'transition tw:group-hover:brightness-40': !isSelected,
        'tw:cursor-pointer': !isAnyImageSelected || isSelected,
      }"
      @click="handlePreview"
    />

    <!-- Tags -->
    <div
      v-if="image.has_variants || image.selected"
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:p-3"
      :class="{
        'tw:opacity-0': isSelected,
        'tw:transition tw:group-hover:opacity-0': !isSelected,
      }"
    >
      <div class="tw:flex tw:flex-wrap tw:gap-1">
        <Chip v-if="image.selected" color="success" leftIcon="tabler:check">
          {{ $t("image-studio.generation-card.selected") }}
        </Chip>

        <Chip
          v-if="image.has_variants"
          color="primary"
          leftIcon="tabler:stack-2"
        >
          {{ $t("image-studio.generation-card.variants") }}
        </Chip>
      </div>
    </div>

    <!-- Actions that are visible on mouse hover -->
    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:flex tw:flex-col tw:justify-between tw:p-3"
      :class="{
        'tw:opacity-0 tw:transition tw:group-hover:opacity-100': !isSelected,
      }"
    >
      <!-- Header -->
      <div class="tw:flex tw:justify-between">
        <!-- Selection checkbox -->
        <FieldBaseRadio
          :name="props.image.id.toString()"
          v-model="selectedImage"
          :value="props.image"
          size="lg"
          variant="switch"
          :disabled="disabled"
        />

        <div
          v-if="!isAnyImageSelected"
          class="tw:flex tw:justify-end tw:gap-4 tw:text-white"
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
            :disabled="disabled"
            :class="{ 'tw:opacity-50': disabled }"
            @click="emit('delete')"
          >
            <Icon icon="tabler:trash" class="tw:text-[20px]" />
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div
        v-if="
          !isAnyImageSelected &&
          !readOnly &&
          (enableMoreLikeThis || enableEditing)
        "
        class="tw:flex tw:gap-2 tw:self-end"
      >
        <!-- More Like This button -->
        <Button
          v-if="enableMoreLikeThis"
          type="button"
          leftIcon="custom:hi-luca"
          size="sm"
          variant="label"
          color="primary"
          class="tw:pointer-events-auto"
          @click="emit('moreLikeThis')"
        >
          {{ $t("image-studio.generation-card.more-like-this") }}
        </Button>

        <!-- Edit button -->
        <Button
          v-if="enableEditing"
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

    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:bg-white tw:opacity-0"
      :class="{
        'tw:opacity-50': selectedImage && !isSelected,
      }"
    ></div>
  </div>
</template>
