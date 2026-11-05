<script setup lang="ts">
import {
  AdChannelAttribute,
  AdChannelAttributePayload,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  index: number;
  name: string;
  canBeDeleted?: boolean;
  generateFn?: (channelAttribute: AdChannelAttribute) => Promise<string[]>;
  bulkGeneratedTexts?: string[];
  disabled?: boolean;
}>();

const emit = defineEmits<{ delete: [] }>();

const { t } = useI18n();

const channelAttribute = useFieldValue<AdChannelAttribute>(() => props.name);
const payloadsField = useFieldArray<AdChannelAttributePayload>(
  () => `${props.name}.payloads`,
);

const isLoading = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);
const generatedTexts = ref<string[]>([]);
const { currentIndex: selectedGeneratedIndex, move: moveGeneratedText } =
  useSliderRef(generatedTexts);

const maxCharacters = computed(() => channelAttribute.value.max_char);

function updatePayloadAtIndex(index: number, text: string) {
  payloadsField.update(index, {
    ...payloadsField.fields.value[index].value,
    payload: text,
  });
}

watch(selectedGeneratedIndex, (newIndex, oldIndex) => {
  // Save the value in the old index
  if (oldIndex !== undefined) {
    generatedTexts.value[oldIndex] =
      payloadsField.fields.value[props.index].value.payload;
  }

  if (newIndex !== undefined) {
    updatePayloadAtIndex(props.index, generatedTexts.value[newIndex]);
  }
});

// Sync external generated texts
watch(
  () => props.bulkGeneratedTexts,
  (texts) => {
    if (!texts) return;

    generatedTexts.value = [...texts];
    selectedGeneratedIndex.value = 0;
    updatePayloadAtIndex(props.index, texts[0]);
  },
  { immediate: true },
);

async function handleGenerateText() {
  if (!props.generateFn) return;

  try {
    generalErrorMessage.value = undefined;

    // Loading
    isLoading.value = true;

    // Generate texts
    const texts = await props.generateFn(channelAttribute.value);
    generatedTexts.value = texts;
    selectedGeneratedIndex.value = 0;

    // Replace text
    updatePayloadAtIndex(props.index, texts[0]);
  } catch (e: unknown) {
    console.error(e);

    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.generate-text-error",
    );
  } finally {
    // Loading
    isLoading.value = false;
  }
}

const disabled = computed(() => isLoading.value || props.disabled);
</script>

<template>
  <div :class="{ 'tw:pointer-events-none tw:opacity-50': disabled }">
    <FieldLabel v-if="index === 0">
      {{
        $t(
          `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.label`,
        )
      }}
    </FieldLabel>

    <div class="tw:flex tw:items-start tw:gap-2">
      <div class="tw:flex tw:grow tw:flex-col">
        <FieldTextarea
          :name="`${props.name}.payloads[${index}].payload`"
          :placeholder="
            $t(
              `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.placeholder`,
            )
          "
          :maxCharacters="maxCharacters"
          :rows="1"
          characterCounter
          required
        >
          <template #right>
            <Tooltip>
              <Button
                icon="custom:hi-luca"
                type="button"
                size="xs"
                @click="handleGenerateText()"
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

      <Tooltip v-if="index === 0" placement="top">
        <Button
          type="button"
          variant="label"
          color="primary"
          icon="custom:pin-filled"
          :shadow="false"
          disabled
        />

        <template #content>
          {{ $t("funnel-flow.paid-social.ads.refine.editor.pinned-format") }}
        </template>
      </Tooltip>

      <Button
        v-else-if="canBeDeleted"
        type="button"
        variant="outlined"
        color="secondary"
        icon="tabler-x"
        @click="emit('delete')"
      />
    </div>
  </div>
</template>
