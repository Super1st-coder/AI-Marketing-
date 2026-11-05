<script setup lang="ts">
import {
  AdMediaElement,
  getAdMediaElementDisplayName,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { getWarningLimit } from "@/utils/text-limits";

const props = defineProps<{
  name: string;
  disabled?: boolean;
  generateFn?: (element: AdMediaElement) => Promise<string[]>;
  bulkGeneratedTexts?: string[];
}>();

const validateIntention = useValidateField(`${props.name}.intention`);

const { value: model, setValue } = useField<AdMediaElement>(() => props.name);

const { t } = useI18n();

const elementValues = [
  "No generate",
  "Headline",
  "Hook",
  "Punchline",
  "Legal",
  "Description",
  "Discount",
  "Pricing",
  "Offer",
  "CTA",
  "Benefit 1",
  "Benefit 2",
  "Benefit 3",
  "Feature 1",
  "Feature 2",
  "Feature 3",
];
const elementIntentionOptions = computed(() =>
  elementValues.map((value) => ({
    label: t(
      `funnel-flow.paid-social.ads.refine.editor.elementIntentionOptions.${value}`,
    ),
    value,
  })),
);

const isLoading = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);
const generatedTexts = ref<string[]>([]);
const { currentIndex: selectedGeneratedIndex, move: moveGeneratedText } =
  useSliderRef(generatedTexts);

watch(selectedGeneratedIndex, (newIndex, oldIndex) => {
  // Save the value in the old index
  if (oldIndex !== undefined) {
    generatedTexts.value[oldIndex] = model.value.payload;
  }

  if (newIndex !== undefined) {
    setValue({ ...model.value, payload: generatedTexts.value[newIndex] });
  }
});

// Sync external generated texts
watch(
  () => props.bulkGeneratedTexts,
  (texts) => {
    if (!texts) return;

    generatedTexts.value = [...texts];
    selectedGeneratedIndex.value = 0;
    setValue({ ...model.value, payload: generatedTexts.value[0] });
  },
  { immediate: true },
);

const handleGenerateText = async () => {
  const { valid } = await validateIntention();
  if (!valid || !props.generateFn) return;

  try {
    generalErrorMessage.value = undefined;
    isLoading.value = true;

    // Generate new texts
    const texts = await props.generateFn(model.value);

    // Replace text
    generatedTexts.value = texts;
    selectedGeneratedIndex.value = 0;
    setValue({ ...model.value, payload: texts[0] });
  } catch (e: unknown) {
    console.error(e);

    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.generate-text-error",
    );
  } finally {
    isLoading.value = false;
  }
};

const isDisabled = computed(() => props.disabled || isLoading.value);
</script>

<template>
  <div
    class="tw:relative"
    :class="{ 'tw:pointer-events-none tw:opacity-50': isDisabled }"
  >
    <FieldLabel>
      {{ getAdMediaElementDisplayName(model.name) }}
    </FieldLabel>

    <div class="tw:flex tw:flex-col tw:gap-2 tw:xl:flex-row tw:xl:gap-6">
      <FieldSelect
        class="tw:basis-1/3"
        :name="`${name}.intention`"
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.refine.editor.elementIntentionPlaceholder',
          )
        "
        :options="elementIntentionOptions"
      />

      <div class="tw:flex tw:basis-2/3 tw:flex-col">
        <FieldTextarea
          :name="`${name}.payload`"
          :placeholder="
            $t(
              'funnel-flow.paid-social.ads.refine.editor.elementPayloadPlaceholder',
              {
                elementName: getAdMediaElementDisplayName(model.name),
              },
            )
          "
          required
          :rows="2"
          :maxCharacters="model.max_char"
          characterCounter
          :warningLimit="
            model.max_char ? getWarningLimit(model.max_char) : undefined
          "
        >
          <template #right>
            <Tooltip>
              <Button
                icon="custom:hi-luca"
                type="button"
                size="xs"
                @click="handleGenerateText"
                :isLoading="isLoading"
              />

              <template #content>
                {{
                  $t(
                    "funnel-flow.paid-social.ads.refine.editor.generate-text-tooltip",
                  )
                }}
              </template>
            </Tooltip>
          </template>
        </FieldTextarea>

        <GeneratedValueSlider
          :currentIndex="selectedGeneratedIndex"
          :itemCount="generatedTexts.length"
          @move="moveGeneratedText"
          class="tw:self-end"
        >
          {{ $t("funnel-flow.paid-social.ads.refine.editor.ai-variations") }}
        </GeneratedValueSlider>

        <Alert
          v-if="generalErrorMessage"
          type="error"
          autoScroll
          class="tw:mt-2"
        >
          {{ generalErrorMessage }}
        </Alert>
      </div>
    </div>
  </div>
</template>
