<script lang="ts" setup>
const props = defineProps<{
  initialSelected?: ImageStudioPhotographicEffect;
}>();

const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  select: [effect: ImageStudioPhotographicEffect];
}>();

const itemRefs = useTemplateRef("items");
const selectedEffect = ref<ImageStudioPhotographicEffect | undefined>(
  props.initialSelected,
);

const isSelectDisabled = computed(() => selectedEffect.value === undefined);

function handleSelectEffect(effect: ImageStudioPhotographicEffect) {
  selectedEffect.value = effect;
}

function handleConfirmSelect() {
  if (!selectedEffect.value) {
    return;
  }

  emit("select", selectedEffect.value);
}

// Scroll to selected item on mount
onMounted(async () => {
  const targetStyle = props.initialSelected;

  if (targetStyle && itemRefs.value) {
    const targetIndex = IMAGE_STUDIO_PHOTOGRAPHIC_EFFECTS.findIndex(
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
      {{ $t("image-studio.photographic-effects.title") }}
    </ModalHeader>

    <ModalBody>
      <div
        class="tw:grid tw:grid-cols-1 tw:gap-7 tw:sm:grid-cols-2 tw:lg:grid-cols-4"
      >
        <CardBase
          v-for="effect in IMAGE_STUDIO_PHOTOGRAPHIC_EFFECTS"
          ref="items"
          is="button"
          class="tw:p-3"
          hoverColor="primary"
          :color="selectedEffect?.name === effect.name ? 'primary' : 'default'"
          @click="handleSelectEffect(effect)"
        >
          <img :src="effect.image_url" class="tw:rounded-xl" />

          <h3 class="tw:mt-2.5 tw:text-sm tw:font-semibold">
            {{ $t(`image-studio.photographic-effects.${effect.name}.title`) }}
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
        type="button"
        :disabled="isSelectDisabled"
        @click="handleConfirmSelect"
      >
        {{ $t("image-studio.photographic-effects.select") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
