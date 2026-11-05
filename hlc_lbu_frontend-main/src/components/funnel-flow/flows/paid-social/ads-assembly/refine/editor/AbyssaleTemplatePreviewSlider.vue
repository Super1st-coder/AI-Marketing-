<script setup lang="ts">
import {
  AdMediaFormat,
  getPinnedOrNearestFourFiveFormatIndex,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{ formats: AdMediaFormat[] }>();
const emit = defineEmits<{
  changeFormat: [format: AdMediaFormat];
}>();

const { value: pinnedFormat } = useField<string | undefined>("pinned_format");
const errorMessage = useFieldError("pinned_format");

function getInitialPreviewIndex(formats: AdMediaFormat[]): number {
  const pinnedPreview = formats.find(
    (format) => format.id === pinnedFormat.value,
  );
  if (pinnedPreview) {
    const pinnedIndex = formats.indexOf(pinnedPreview);
    if (pinnedIndex >= 0) return pinnedIndex;
  }

  return getPinnedOrNearestFourFiveFormatIndex(formats);
}

const selectedPreviewIndex = ref(getInitialPreviewIndex(props.formats));
const selectedPreview = computed(
  () => props.formats?.[selectedPreviewIndex.value],
);
const isSelectedFormatPinned = computed(
  () => selectedPreview.value?.id === pinnedFormat.value,
);

watch(
  () => selectedPreview.value,
  (newPreview) => {
    if (newPreview) {
      emit("changeFormat", newPreview);
    }
  },
  { immediate: true },
);

const handleChangePreview = (direction: number) => {
  let targetIndex = selectedPreviewIndex.value + direction;
  if (targetIndex > (props.formats?.length ?? 0) - 1) targetIndex = 0;
  if (targetIndex < 0) targetIndex = (props.formats?.length ?? 0) - 1;
  selectedPreviewIndex.value = targetIndex;
};

function handlePinFormat() {
  if (!selectedPreview.value) return;

  pinnedFormat.value = isSelectedFormatPinned.value
    ? undefined
    : selectedPreview.value.id;
}
</script>

<template>
  <CardBase
    v-if="selectedPreview"
    class="tw:flex tw:flex-col tw:gap-6 tw:px-5 tw:py-6"
  >
    <div class="tw:flex tw:flex-col tw:items-center">
      <h3
        class="tw:relative tw:mb-2 tw:w-full tw:text-center tw:text-2xl tw:leading-none tw:font-extrabold"
      >
        {{ selectedPreview.id }}

        <div class="tw:absolute tw:top-1/2 tw:right-0 tw:-translate-y-1/2">
          <Tooltip placement="top">
            <Button
              :icon="
                isSelectedFormatPinned ? 'custom:pin-filled' : 'tabler:pin'
              "
              name="pinned_format"
              size="sm"
              type="button"
              :color="
                errorMessage
                  ? 'error'
                  : isSelectedFormatPinned
                    ? 'primary'
                    : 'secondary'
              "
              :variant="isSelectedFormatPinned ? 'label' : 'outlined'"
              :shadow="false"
              @click="handlePinFormat"
            />

            <template #content>
              {{
                $t(
                  isSelectedFormatPinned
                    ? "funnel-flow.paid-social.ads.refine.editor.pinned-format"
                    : "funnel-flow.paid-social.ads.refine.editor.pin-format",
                )
              }}
            </template>
          </Tooltip>
        </div>
      </h3>

      <span>
        {{ selectedPreview.width }}X{{ selectedPreview.height }}
        {{ selectedPreview.unit }}
      </span>

      <FieldError v-if="errorMessage">
        {{ errorMessage }}
      </FieldError>
    </div>

    <div>
      <ImgAndPdf
        :key="selectedPreview.preview_url"
        :src="selectedPreview.visual_url ?? selectedPreview.preview_url"
        class="tw:mx-auto tw:mb-2 tw:aspect-4/5 tw:rounded-xl tw:border-2 tw:bg-gray-100 tw:object-contain"
        style="max-width: 282px"
      />

      <div class="tw:text-center tw:text-xs">
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.preview-position", {
            current: selectedPreviewIndex + 1,
            total: formats.length,
          })
        }}
      </div>
    </div>

    <div class="tw:flex tw:grow tw:justify-center tw:gap-4">
      <Button
        type="button"
        icon="tabler-chevron-left"
        size="xs"
        variant="text"
        color="default"
        @click="handleChangePreview(-1)"
      />

      <Button
        type="button"
        icon="tabler-chevron-right"
        size="xs"
        variant="text"
        color="default"
        @click="handleChangePreview(1)"
      />
    </div>
  </CardBase>
</template>
