<script setup lang="ts">
import Modal from "@/components/modals/base/Modal.vue";
import ImageLibrary from "./ImageLibrary.vue";
import { ImageLibrarySource } from "./image-library.types.ts";

const isOpen = defineModel<boolean>({ required: true });

interface Props {
  maxWidth?: number | string;
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
  customSources?: ImageLibrarySource[];
}

const props = withDefaults(defineProps<Props>(), {
  maxWidth: 1066,
  accept: undefined,
  cropper: undefined,
  aspectRatio: undefined,
  disabled: undefined,
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="props.maxWidth"
    :radius="20"
    alignment="top"
    closeButton
    :innerClass="'tw:overflow-hidden'"
  >
    <ImageLibrary
      v-if="isOpen"
      :accept="props.accept"
      :cropper="props.cropper"
      :aspectRatio="props.aspectRatio"
      :disabled="props.disabled"
      :customSources="customSources"
    >
      <!-- Pass all the slots -->
      <template v-for="(_, name) in $slots" :key="name" #[name]="scope">
        <slot :name v-bind="scope ?? {}" />
      </template>
    </ImageLibrary>
  </Modal>
</template>
