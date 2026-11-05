<script setup lang="ts">
// `undefined` keeps the image as it is
const expandZoom = defineModel<ImageStudioExpandZoom | undefined>({
  required: true,
});

const { t } = useI18n();

const selectedOption = computed(() =>
  [
    ...IMAGE_STUDIO_EXPAND_ZOOM_DIRECTIONAL,
    ...IMAGE_STUDIO_EXPAND_ZOOM_UNIFORM,
  ].find((option) => option.value === expandZoom.value),
);

const buttonIcon = computed(() => selectedOption.value?.icon ?? "tabler:zoom");

const buttonLabel = computed(() => {
  if (!selectedOption.value) {
    return t("image-studio.expand-zoom-image");
  }

  if (
    IMAGE_STUDIO_EXPAND_ZOOM_DIRECTIONAL.some(
      (option) => option.value === expandZoom.value,
    )
  ) {
    return t("image-studio.expand-zoom.expand-selected", {
      direction: t(`image-studio.expand-zoom.${selectedOption.value.labelKey}`),
    });
  }

  return t("image-studio.expand-zoom.zoom-out-selected", {
    scale: t(`image-studio.expand-zoom.${selectedOption.value.labelKey}`),
  });
});
</script>

<template>
  <ButtonDropdown
    placement="top"
    variant="text"
    color="secondary"
    :leftIcon="buttonIcon"
    size="md"
  >
    {{ buttonLabel }}

    <template #options>
      <div class="tw:flex tw:min-w-[198px] tw:flex-col">
        <ButtonDropdownHeading uppercase>
          {{ $t("image-studio.expand-zoom.directional-expand") }}
        </ButtonDropdownHeading>

        <ButtonDropdownOption
          v-for="option in IMAGE_STUDIO_EXPAND_ZOOM_DIRECTIONAL"
          :key="option.value"
          :leftIcon="option.icon"
          :selected="expandZoom === option.value"
          @click="expandZoom = option.value"
        >
          {{ $t(`image-studio.expand-zoom.${option.labelKey}`) }}
        </ButtonDropdownOption>

        <ButtonDropdownSeparator />

        <ButtonDropdownHeading uppercase>
          {{ $t("image-studio.expand-zoom.uniform-zoom-out") }}
        </ButtonDropdownHeading>

        <ButtonDropdownOption
          v-for="option in IMAGE_STUDIO_EXPAND_ZOOM_UNIFORM"
          :key="option.value"
          :leftIcon="option.icon"
          :selected="expandZoom === option.value"
          @click="expandZoom = option.value"
        >
          {{ $t(`image-studio.expand-zoom.${option.labelKey}`) }}
        </ButtonDropdownOption>

        <ButtonDropdownSeparator />

        <ButtonDropdownOption
          leftIcon="tabler:square"
          :selected="expandZoom === undefined"
          @click="expandZoom = undefined"
        >
          {{ $t("image-studio.expand-zoom.original-none") }}
        </ButtonDropdownOption>
      </div>
    </template>
  </ButtonDropdown>
</template>
