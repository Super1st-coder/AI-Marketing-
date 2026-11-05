<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";
import { AssetsFormData } from "./AssetsForm.vue";
import AssetsApi from "@/services/legacy/AssetsApi";
import { UnidentifiedError } from "@/services/common-errors";
import { useQuery } from "@tanstack/vue-query";

const appLocaleData = useAppLocaleData();
const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<Required<AssetsFormData>>();

if (!data.value.currentTemplateId) {
  throw new UnidentifiedError();
}

// Load template
const { suspense } = useQuery({
  queryKey: [
    "brand",
    brandId,
    "project",
    projectId,
    "campaign",
    campaignId,
    "template",
    data.value.currentTemplateId,
  ],
  queryFn: async () => {
    // Fetch the template
    const { data: response } = await AssetsApi.getOneTemplate(
      brandId,
      projectId,
      campaignId,
      data.value.currentTemplateId,
    );

    // Save template in the data
    saveData({ currentTemplate: response });

    return response;
  },
  refetchInterval: computed(() =>
    data.value.currentTemplate?.generation_request_pending ? 6000 : false,
  ),
});
await suspense();

// Load images
const imagePromises = data.value.currentTemplate.images.map(async (image) => {
  const response = await AssetsApi.getTemplateImage(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    image.name,
  );

  return {
    name: image.name,
    image: response,
  };
});
const initialImages = await Promise.all(imagePromises);

const schema = computed(() =>
  toTypedSchema(
    object({
      tone: string().required(t("forms.required-field")),
      language: string().required(t("forms.required-field")),
      extra_context: string()
        .required(t("forms.required-field"))
        .max(250, ({ max }) => t("forms.max-characters", { max })),
      elements: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            type: string().required(t("forms.required-field")),
            payload: string().required(t("forms.required-field")),
            intention: string().required(t("forms.required-field")),
            original_payload: string(),
          }),
        )
        .required(t("forms.required-field")),
      images: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            image: mixed<Blob>(),
          }),
        )
        .required(t("forms.required-field")),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  values,
  setFieldValue,
  validateField,
  meta,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  keepValuesOnUnmount: true,
  initialValues: {
    tone: data.value.currentTemplate.tone ?? undefined,
    language:
      data.value.currentTemplate.language ??
      appLocaleData.value.apiName ??
      undefined,
    extra_context: data.value.currentTemplate.extra_context ?? undefined,
    elements: data.value.currentTemplate.elements
      .map((element) => ({
        ...element,
        payload: element.payload ?? "",
        intention: element.intention ?? "",
      }))
      .sort((a, b) => a.name.localeCompare(b.name, "en", { numeric: true })),
    images: initialImages,
  },
});

const saveSuccessMessage = ref<string>();
const sendMode = ref<"save" | "abyssale">();

const onSubmit = handleSubmit(async (values) => {
  if (!sendMode.value) {
    sendMode.value = "save";
  }

  // Clear success message
  saveSuccessMessage.value = undefined;
  try {
    // Send data
    const { data: response } = await AssetsApi.saveTemplate(
      brandId,
      projectId,
      campaignId,
      data.value.currentTemplate.template_id,
      {
        tone: values.tone,
        extra_context: values.extra_context,
        language: values.language,
        generate_visual: sendMode.value === "abyssale",
        elements: values.elements ?? [],
      },
    );

    // Save response in data
    saveData({
      currentTemplate: { ...data.value.currentTemplate, ...response },
    });

    // Save images
    const imagePromises = values.images.map(async (uploadedImageData) => {
      if (uploadedImageData.image) {
        await AssetsApi.uploadTemplateImage(
          brandId,
          projectId,
          campaignId,
          data.value.currentTemplate.template_id,
          uploadedImageData.name,
          uploadedImageData.image,
        );
      }
    });
    await Promise.all(imagePromises);

    // Success message
    if (sendMode.value === "save") {
      saveSuccessMessage.value = t(
        "campaigns.assets.builder.messagebuttonsaveimage",
      );

      // Delete the success message after a while
      setTimeout(() => {
        saveSuccessMessage.value = undefined;
      }, 5000);
    }
  } catch (error) {
    console.error(error);
  } finally {
    sendMode.value = undefined;
  }
});

const handleSendToAbyssale = async () => {
  sendMode.value = "abyssale";
  onSubmit();
};

const selectedPreviewIndex = ref(0);
const selectedPreview = computed(
  () => data.value.currentTemplate.formats[selectedPreviewIndex.value],
);

const handleChangePreview = (direction: number) => {
  let targetIndex = selectedPreviewIndex.value + direction;
  if (targetIndex > data.value.currentTemplate.formats.length - 1)
    targetIndex = 0;
  if (targetIndex < 0)
    targetIndex = data.value.currentTemplate.formats.length - 1;
  selectedPreviewIndex.value = targetIndex;
};

const isGeneratingTexts = ref(false);
const handleGenerateTexts = async () => {
  if (!values.elements) {
    return;
  }

  const incompletedElements =
    values.elements?.filter((element) => !element.intention) ?? [];

  // Check elements
  if (incompletedElements.length > 0) {
    if (incompletedElements.length > 0) {
      for (const incompleteElement of incompletedElements) {
        if (!incompleteElement.intention) {
          const index = values.elements.findIndex(
            (element) => element.name === incompleteElement.name,
          );

          validateField(`elements.${index}.intention`);
        }
      }
    }
  }

  const { valid: isToneValid } = await validateField("tone");
  const { valid: isExtraContextValid } = await validateField("extra_context");

  // Check needed fields
  if (!isToneValid || !isExtraContextValid || incompletedElements.length > 0) {
    return;
  }

  // Generate the texts
  isGeneratingTexts.value = true;
  const { data: generatedElements } = await AssetsApi.generateTexts(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    {
      tone: values.tone,
      extra_context: values.extra_context,
      elements: values.elements,
      language: values.language,
    },
  );
  isGeneratingTexts.value = false;

  // Set the texts
  for (const generatedElement of generatedElements) {
    if (generatedElement.payload) {
      const index = values.elements.findIndex(
        (element) => element.name === generatedElement.name,
      );
      setFieldValue(`elements.${index}.payload`, generatedElement.payload);
    }
  }
};

const handleGenerateImageWithAi = async (index: number) => {
  const { valid: isToneValid } = await validateField("tone");
  const { valid: isExtraContextValid } = await validateField("extra_context");
  const { valid: areElementsValid } = await validateField("elements");

  // Check needed fields
  if (!isToneValid || !isExtraContextValid || !areElementsValid) {
    return;
  }

  try {
    await AssetsApi.saveTemplate(
      brandId,
      projectId,
      campaignId,
      data.value.currentTemplate.template_id,
      {
        tone: values.tone,
        extra_context: values.extra_context,
        language: values.language,
        generate_visual: false,
        elements: values.elements ?? [],
      },
    );
    saveData({ currentImageIndex: index });
  } catch (error) {
    console.error(error);
  } finally {
    sendMode.value = undefined;
  }

  saveData({ currentImageIndex: index });
};

const toneOptions = computed(() => [
  {
    label: t("campaigns.assets.builder.toneOptions.positive"),
    value: "Positive",
  },
  {
    label: t("campaigns.assets.builder.toneOptions.negative"),
    value: "Negative",
  },
  { label: t("campaigns.assets.builder.toneOptions.happy"), value: "Happy" },
  {
    label: t("campaigns.assets.builder.toneOptions.motivational"),
    value: "Motivational",
  },
  {
    label: t("campaigns.assets.builder.toneOptions.hardSeller"),
    value: "Hard Seller",
  },
]);

const displayAbyssalePendingAlert = computed(
  () =>
    (isSubmitting && sendMode.value === "abyssale") ||
    data.value.currentTemplate.generation_request_pending,
);

const abyssaleFormatsWithErrors = computed(() =>
  data.value.currentTemplate.formats.filter((template) =>
    template.errors ? template.errors.length > 0 : false,
  ),
);

const displayAbyssaleErrors = computed(
  () =>
    !displayAbyssalePendingAlert.value &&
    abyssaleFormatsWithErrors.value.length > 0,
);

const textFittingSolutionMessage = computed(() => {
  const formatsWithTextFittingErrors = abyssaleFormatsWithErrors.value
    .filter((format) =>
      format.errors?.some((error) =>
        error.includes("cannot fit within the defined space"),
      ),
    )
    .map((format) => `Format ${format.id}`);

  if (formatsWithTextFittingErrors.length === 0) return undefined;

  return t(
    "campaigns.assets.builder.abyssale-error.text-auto-resize-solution",
    {
      formats: formatsWithTextFittingErrors.join(", "),
    },
  );
});

// Display success message if the generation isn't pending anymore
const abyssaleSuccessMessage = ref<string>();
watch(
  () => data.value.currentTemplate.generation_request_pending,
  (isPending) => {
    if (!isPending && abyssaleFormatsWithErrors.value.length === 0) {
      abyssaleSuccessMessage.value = t(
        "campaigns.assets.builder.messageconfirmabyssale",
      );

      // Delete the success message after a while
      setTimeout(() => {
        abyssaleSuccessMessage.value = undefined;
      }, 5000);
    }
  },
);

// Hide success meessage if the generation is pending again
watch(displayAbyssalePendingAlert, (value) => {
  if (value) {
    abyssaleSuccessMessage.value = undefined;
  }
});

const { confirm } = useConfirmModal("delivery");

const handleConfirmDelivery = async () => {
  const answer = await confirm();
  if (answer === "continue") {
    goNext();
  }
};
</script>

<template>
  <FormStepLayout
    v-if="data.currentImageIndex === undefined"
    @submit.prevent="onSubmit"
  >
    <PageTitle helpButton>
      {{ $t("campaigns.assets.builder.title") }}

      <template #description>
        {{ $t("campaigns.assets.builder.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-6 tw:xl:flex-row tw:xl:items-start">
      <!-- Preview and save buttons -->
      <div
        class="tw:flex tw:flex-col tw:gap-4 tw:overflow-y-auto tw:xl:sticky tw:xl:top-20 tw:xl:max-h-[calc(100vh-200px)] tw:xl:shrink-0 tw:xl:grow-0 tw:xl:basis-[354px]"
      >
        <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
          <h3
            class="tw:flex tw:flex-col tw:items-center tw:text-2xl tw:font-extrabold"
          >
            <div>{{ selectedPreview.id }}</div>
            <div class="tw:text-base tw:font-medium">
              {{ selectedPreview.width }}X{{ selectedPreview.height }}
              {{ selectedPreview.unit }}
            </div>
          </h3>

          <img
            :key="selectedPreview.preview_url"
            :src="selectedPreview.preview_url"
            class="tw:aspect-square tw:w-full tw:rounded-md tw:border-2 tw:border-dashed tw:border-gray-300 tw:object-contain"
          />
          <div class="tw:text-center tw:text-xs tw:text-gray-500">
            {{ selectedPreviewIndex + 1 }} of
            {{ data.currentTemplate.formats.length }}
          </div>
          <div class="tw:flex tw:justify-center">
            <Button
              type="button"
              icon="tabler-chevron-left"
              size="sm"
              variant="text"
              color="default"
              @click="handleChangePreview(-1)"
            />

            <Button
              type="button"
              icon="tabler-chevron-right"
              size="sm"
              variant="text"
              color="default"
              @click="handleChangePreview(1)"
            />
          </div>
        </CardBase>

        <!-- Success save alert -->
        <Alert v-if="saveSuccessMessage" type="success">
          {{ saveSuccessMessage }}
        </Alert>

        <!-- Save button -->
        <Button :isLoading="isSubmitting && sendMode === 'save'">
          {{ $t("global.save") }}
        </Button>

        <!-- Abyssale success save alert -->
        <Alert v-if="abyssaleSuccessMessage" type="success">
          {{ abyssaleSuccessMessage }}
        </Alert>

        <!-- Abyssale pending request alert -->
        <Alert v-if="displayAbyssalePendingAlert" type="secondary">
          {{ $t("campaigns.assets.builder.data-being-sent-to-abyssale") }}
        </Alert>

        <!-- Abyssale errors -->
        <Alert v-if="displayAbyssaleErrors" type="error">
          <template #custom>
            <p>
              {{
                $t(
                  "campaigns.assets.builder.abyssale-error.data-couldnt-be-sent",
                )
              }}<br /><br />
            </p>

            <template v-for="format in abyssaleFormatsWithErrors">
              <i18n-t
                keypath="campaigns.assets.builder.abyssale-error.format"
                tag="p"
              >
                <template #id>
                  <strong>{{ format.id }}</strong>
                </template>
              </i18n-t>

              <ul class="tw:list-disc">
                <li v-for="error in format.errors" class="tw:ml-4">
                  {{ error }}
                </li>
              </ul>

              <br />
            </template>

            <p v-if="textFittingSolutionMessage">
              {{ textFittingSolutionMessage }}
            </p>
          </template>
        </Alert>

        <!-- Send to abyssale button -->
        <Button
          type="button"
          variant="outlined"
          :isLoading="displayAbyssalePendingAlert"
          @click="handleSendToAbyssale"
        >
          {{ $t("campaigns.assets.builder.buttonsendtoabyssale") }}
        </Button>
      </div>

      <!-- Elements -->
      <div
        class="tw:flex tw:shrink tw:grow tw:flex-col tw:gap-6 tw:xl:order-first"
      >
        <h2 class="tw:text-2xl tw:font-extrabold">
          {{ data.currentTemplate.template_name }}
        </h2>

        <FieldSelect
          name="tone"
          :label="$t('campaigns.assets.builder.toneLabel')"
          :placeholder="$t('campaigns.assets.builder.tonePlaceholder')"
          required
          :options="toneOptions"
        />

        <FieldLanguage
          name="language"
          :label="$t('campaigns.assets.builder.languagelabel')"
          orientation="vertical"
          required
        />

        <FieldTextarea
          name="extra_context"
          :label="$t('campaigns.assets.builder.extraContextLabel')"
          :placeholder="$t('campaigns.assets.builder.extraContextPlaceholder')"
          speechRecognition
          required
          :options="toneOptions"
          :maxCharacters="250"
        />

        <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
          <h3 class="tw:text-2xl tw:font-extrabold">
            {{ $t("campaigns.assets.builder.templateTextsTitle") }}
          </h3>

          <AssetsFormBuilderElementField
            v-for="(_element, index) in values.elements"
            :templateId="data.currentTemplate.template_id"
            :name="`elements[${index}]`"
          />

          <Button
            class="tw:self-end"
            leftIcon="custom:hi-luca"
            type="button"
            :isLoading="isGeneratingTexts"
            @click="handleGenerateTexts"
          >
            {{ $t("campaigns.assets.builder.buttonGenerateText") }}
          </Button>
        </CardBase>

        <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
          <h3 class="tw:text-2xl tw:font-extrabold">
            {{ $t("campaigns.assets.builder.imagesTitle") }}
          </h3>

          <div
            v-for="(image, index) in data.currentTemplate.images"
            class="tw:flex tw:max-w-[325px] tw:flex-col"
          >
            <FieldImage
              :label="anyCaseToText(image.name)"
              :name="`images[${index}].image`"
              :previewSrc="image.preview_url"
              cropper
            />

            <Button
              class="tw:mt-2.5 tw:self-end"
              leftIcon="custom:hi-luca"
              type="button"
              @click="handleGenerateImageWithAi(index)"
            >
              {{ $t("campaigns.assets.builder.buttongeneratewith") }}
            </Button>
          </div>
        </CardBase>
      </div>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />

        <ButtonNext @click="handleConfirmDelivery" type="button">
          {{ $t("campaigns.assets.builder.buttonAssetDelivery") }}
        </ButtonNext>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />

    <ModalConfirmGeneric
      name="delivery"
      displayShowCheckbox
      imageSrc="/images/emojis/incoming-envelope.png"
    >
      <template #title>
        {{ $t("campaigns.assets.builder.modal-confirm-generic.title") }}
      </template>

      <template #description>
        {{ $t("campaigns.assets.builder.modal-confirm-generic.description") }}
      </template>

      <template #cancel> {{ $t("global.cancel") }} </template>
      <template #continue>
        {{
          $t("campaigns.assets.builder.modal-confirm-generic.continueButton")
        }}
      </template>
    </ModalConfirmGeneric>
  </FormStepLayout>
  <AssetsFormBuilderImage v-if="data.currentImageIndex !== undefined" />
</template>
