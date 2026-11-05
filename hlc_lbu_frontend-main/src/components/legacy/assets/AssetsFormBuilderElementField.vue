<script setup lang="ts">
import AssetsApi from "@/services/legacy/AssetsApi";

const props = defineProps<{ name: string; templateId: string }>();

const tone = useFieldValue<string | undefined>("tone");
const validateTone = useValidateField("tone");

const extraContext = useFieldValue<string | undefined>("extra_context");
const validateExtraContext = useValidateField("extra_context");

const validateElements = useValidateField("elements");
const language = useFieldValue<string | undefined>("language");

const { value: model, setValue } = useField<{
  name: string;
  type: string;
  payload: string;
  intention: string;
  original_payload?: string;
}>(() => props.name);

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const elementIntentionOptions = computed(() => [
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.nogenerate"),
    value: "No generate",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.headline"),
    value: "Headline",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.hook"),
    value: "Hook",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.punchline"),
    value: "Punchline",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.legal"),
    value: "Legal",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.description"),
    value: "Description",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.discount"),
    value: "Discount",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.pricing"),
    value: "Pricing",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.offer"),
    value: "Offer",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.cta"),
    value: "CTA",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.benefit1"),
    value: "Benefit 1",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.benefit2"),
    value: "Benefit 2",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.benefit3"),
    value: "Benefit 3",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.feature1"),
    value: "Feature 1",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.feature2"),
    value: "Feature 2",
  },
  {
    label: t("campaigns.assets.builder.elementIntentionOptions.feature3"),
    value: "Feature 3",
  },
]);

const isLoading = ref(false);
const handleGenerateText = async () => {
  const { valid: isToneValid } = await validateTone();
  const { valid: isExtraContextValid } = await validateExtraContext();
  const { valid: areElementsValid } = await validateElements();

  // Check needed fields
  if (!isToneValid || !isExtraContextValid || !areElementsValid) {
    return;
  }

  isLoading.value = true;

  const { data: response } = await AssetsApi.generateText(
    brandId,
    projectId,
    campaignId,
    props.templateId,
    {
      tone: tone.value,
      extra_context: extraContext.value,
      element: model.value,
      language: language.value,
    },
  );

  isLoading.value = false;

  if (response.payload) {
    setValue({ ...model.value, payload: response.payload });
  }
};

const maxCharacters = computed(() => {
  if (!model.value.original_payload) {
    return undefined;
  }

  const lowerCaseText = model.value.original_payload.toLowerCase();

  const regex = /max\s*char\.?\s*(\d+)/i;
  const match = lowerCaseText.match(regex);

  if (match) {
    return parseInt(match[1], 10);
  }

  return undefined;
});
</script>

<template>
  <div>
    <h4 class="tw:text-lg tw:font-bold">
      {{ anyCaseToText(model.name) }}
    </h4>

    <div class="tw:flex tw:flex-col tw:gap-2 tw:xl:flex-row tw:xl:gap-6">
      <FieldSelect
        class="tw:basis-1/3"
        :name="`${name}.intention`"
        :placeholder="
          $t('campaigns.assets.builder.elementIntentionPlaceholder')
        "
        :options="elementIntentionOptions"
      />

      <FieldTextarea
        class="tw:basis-2/3"
        :name="`${name}.payload`"
        :placeholder="
          $t('campaigns.assets.builder.elementPayloadPlaceholder', {
            elementName: anyCaseToText(model.name),
          })
        "
        required
        :rows="1"
        :maxCharacters="maxCharacters"
        characterCounter
      >
        <template #buttons>
          <Tooltip>
            <Button
              icon="custom:hi-luca"
              type="button"
              @click="handleGenerateText"
              :isLoading="isLoading"
            />

            <template #content>
              {{ $t("campaigns.assets.builder.generate-text-tooltip") }}
            </template>
          </Tooltip>
        </template>
      </FieldTextarea>
    </div>
  </div>
</template>
