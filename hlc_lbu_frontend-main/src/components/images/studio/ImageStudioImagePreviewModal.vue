<script lang="ts" setup>
import { ImageStudioGeneratedImage } from "./types";
import { downloadStudioImage } from "./utils";

defineProps<{
  image: ImageStudioGeneratedImage;
  readOnly?: boolean;
  enableEditing?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{ delete: []; edit: [] }>();
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="1020"
    closeOnClickOutside
    v-slot="{ close }"
  >
    <div
      class="tw:flex tw:flex-col tw:divide-y tw:divide-divider tw:md:flex-row tw:md:divide-x tw:md:divide-y-0"
    >
      <!-- Image -->
      <div class="tw:flex tw:grow tw:justify-center tw:p-6">
        <ImgFile
          :src="image.image_blob ?? image.image_url"
          class="tw:max-h-[672px] tw:rounded-[10px] tw:object-contain tw:select-none"
        />
      </div>

      <div
        class="tw:flex tw:shrink-0 tw:flex-col tw:divide-y tw:divide-divider"
        style="flex-basis: 300px"
      >
        <!-- Header -->
        <div class="tw:flex tw:items-center tw:justify-between tw:p-6">
          <!-- Actions -->
          <div class="tw:flex">
            <!-- Download button -->
            <button
              type="button"
              class="tw:p-3"
              @click="downloadStudioImage(image)"
            >
              <Icon icon="tabler:download" class="tw:text-[20px]" />
            </button>

            <template v-if="!readOnly">
              <div>
                <Separator type="vertical" class="tw:h-[30px]" />
              </div>

              <!-- Delete button -->
              <button type="button" class="tw:p-3" @click="emit('delete')">
                <Icon icon="tabler:trash" class="tw:text-[20px]" />
              </button>
            </template>
          </div>

          <!-- Close button -->
          <div>
            <button type="button" class="tw:p-[3px]" @click="close">
              <Icon icon="tabler:x" class="tw:text-[24px]" />
            </button>
          </div>
        </div>

        <!-- Prompt -->
        <div class="tw:grow tw:p-6">
          <template v-if="image.prompt">
            <h4 class="tw:mb-2.5 tw:text-sm tw:font-semibold">
              {{ $t("image-studio.preview-modal.prompt") }}
            </h4>

            <p class="tw:text-xs tw:leading-5 tw:text-gray-500">
              {{ image.prompt }}
            </p>
          </template>

          <p v-else class="tw:text-sm tw:text-gray-500">
            {{ $t("image-studio.preview-modal.no-prompt") }}
          </p>
        </div>

        <!-- Footer -->
        <div class="tw:flex tw:flex-col tw:gap-3 tw:p-6">
          <Button
            v-if="!readOnly && enableEditing"
            leftIcon="tabler:pencil"
            variant="outlined"
            color="secondary"
            size="sm"
            @click="emit('edit')"
          >
            {{ $t("image-studio.preview-modal.edit-image") }}
          </Button>

          <Button leftIcon="tabler-arrow-left" variant="outlined" size="sm">
            {{ $t("global.back") }}
          </Button>
        </div>
      </div>
    </div>
  </Modal>
</template>
