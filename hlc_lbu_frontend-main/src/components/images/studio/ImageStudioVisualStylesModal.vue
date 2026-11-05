<script lang="ts" setup>
const props = defineProps<{
  customStyles?: ImageStudioVisualStyle[];
  initialSelected?: ImageStudioVisualStyle;
}>();

const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  select: [style: ImageStudioVisualStyle];
  create: [style: ImageStudioVisualStyle];
}>();

const itemRefs = useTemplateRef("items");
const selectedStyle = ref<ImageStudioVisualStyle | undefined>(
  props.initialSelected,
);
const isCreateModalOpen = ref(false);

const allStyles = computed(() => [
  ...(props.customStyles ?? []),
  ...IMAGE_STUDIO_VISUAL_STYLES,
]);

const isSelectDisabled = computed(() => selectedStyle.value === undefined);

function handleSelectStyle(style: ImageStudioVisualStyle) {
  selectedStyle.value = style;
}

function handleConfirmSelect() {
  if (!selectedStyle.value) {
    return;
  }

  emit("select", selectedStyle.value);
}

function handleOpenCreateVisualStyle() {
  isCreateModalOpen.value = true;
}

function handleCreateVisualStyle(style: ImageStudioVisualStyle) {
  isCreateModalOpen.value = false;
  emit("create", style);
}

// Scroll to selected item on mount
onMounted(async () => {
  const targetStyle = props.initialSelected;

  if (targetStyle && itemRefs.value) {
    const targetIndex = allStyles.value.findIndex(
      (style) => style.name === targetStyle.name,
    );
    const targetElement = itemRefs.value[targetIndex]?.element;

    if (targetIndex != -1 && targetElement) {
      scrollElementIntoView(targetElement);
    }
  }
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="958"
    closeButton
    scrollable="inner"
    v-slot="{ close }"
  >
    <ModalHeader>
      {{ $t("image-studio.visual-styles.title") }}
    </ModalHeader>

    <ModalBody>
      <div
        class="tw:grid tw:grid-cols-1 tw:gap-7 tw:sm:grid-cols-2 tw:lg:grid-cols-4"
      >
        <CardBase
          v-for="style in allStyles"
          ref="items"
          is="button"
          class="tw:p-3"
          hoverColor="primary"
          :color="selectedStyle?.name === style.name ? 'primary' : 'default'"
          @click="handleSelectStyle(style)"
        >
          <ImgFile
            :src="style.image ?? style.image_url"
            class="tw:aspect-square tw:rounded-xl tw:bg-gray-500 tw:object-contain"
          />

          <h3 class="tw:mt-2.5 tw:text-sm tw:font-semibold">
            {{
              $te(`image-studio.visual-styles.${style.name}.title`)
                ? $t(`image-studio.visual-styles.${style.name}.title`)
                : style.name
            }}
          </h3>
        </CardBase>
      </div>
    </ModalBody>

    <ModalFooter>
      <template #before>
        <Button
          color="secondary"
          variant="outlined"
          type="button"
          @click="close"
        >
          {{ $t("global.cancel") }}
        </Button>
      </template>

      <Button
        v-if="!IMAGE_STUDIO_DISABLE_CUSTOM_VISUAL_STYLES"
        color="primary"
        variant="label"
        leftIcon="tabler:plus"
        type="button"
        @click="handleOpenCreateVisualStyle"
      >
        {{ $t("image-studio.visual-styles.create") }}
      </Button>

      <Button
        type="button"
        :disabled="isSelectDisabled"
        @click="handleConfirmSelect"
      >
        {{ $t("image-studio.visual-styles.select") }}
      </Button>
    </ModalFooter>

    <!-- Create Visual Style Modal -->
    <ImageStudioCreateVisualStyleModal
      v-if="!IMAGE_STUDIO_DISABLE_CUSTOM_VISUAL_STYLES && isCreateModalOpen"
      v-model="isCreateModalOpen"
      @create="handleCreateVisualStyle"
    />
  </Modal>
</template>
