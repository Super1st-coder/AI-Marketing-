<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdMediaElement,
  getPinnedFormat,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";
import useGenerateAbyssaleVisuals from "../composables/useGenerateAbyssaleVisuals";

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();
const { generateVisuals, isWaitingForAbyssale } = useGenerateAbyssaleVisuals();

const generatePreviews = ref(false);
const isGeneratingAllTexts = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);
const bulkGeneratedSlices = ref<string[][]>([]);
const isPreviewOpen = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      elements: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            type: string().required(t("forms.required-field")),
            payload: string()
              .required(t("forms.required-field"))
              // Check max characters
              .test("maxCharacters", (value, context) => {
                // If there's no original payload, do not limit the character length
                if (!context.parent.original_payload) {
                  return true;
                }

                // Extract the original payload length and use it as the maximun character count
                const length = context.parent.original_payload.length;
                const warningLimit = getWarningLimit(length);

                if (value.length > warningLimit) {
                  return context.createError({
                    message: t("forms.max-characters-opt-2"),
                  });
                }

                return true;
              }),
            intention: string().required(t("forms.required-field")),
            original_payload: string().required(t("forms.required-field")),
            max_char: number().required(t("forms.required-field")),
          }),
        )
        .required(t("forms.required-field")),
      pinned_format: string().required(
        t("funnel-flow.paid-social.ads.refine.editor.pin-format-required"),
      ),
    }),
  ),
);

// Initial values
const initialElements = store.currentVariant?.media.elements
  ?.map((element) => ({
    ...element,
    payload: element.payload ?? "",
    intention: element.intention ?? "",
    max_char: element.original_payload ? element.original_payload.length : 255,
  }))
  .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

const { handleSubmit, isSubmitting, values, meta, submitSuccess } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      elements: initialElements,
      pinned_format: getPinnedFormat(store.currentVariant?.media.formats)?.id,
    },
    validateOnMount: true,
  });

async function save() {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  // Save elements
  await AdsApi.saveMediaElements({
    brand_id: store.brandId,
    campaign_id: store.campaignId,
    ad_id: store.currentAd.ad_id,
    channel_id: store.currentChannel.channel_id,
    variant_id: store.currentVariant.id,
    elements: values.elements ?? [],
  });

  if (values.pinned_format) {
    await AdsApi.pinAdVariantFormat({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: store.currentAd.ad_id,
      channel_id: store.currentChannel.channel_id,
      variant_id: store.currentVariant.id,
      format_id: values.pinned_format,
    });
  }

  // Refetch the ad
  await store.refetchCurrentAd();

  // Revalidate funnel flow
  await paidSocialFormStore.revalidate();

  await sleep(500);
}

const onSubmit = handleSubmit(async (_values) => {
  await save();

  if (generatePreviews.value) {
    // Generate visuals in abyssale
    const success = await generateVisuals();

    if (!success) {
      return;
    }

    isPreviewOpen.value = true;
    generatePreviews.value = false;
  }
});

async function handleSaveAndExit() {
  await save();
}

//#region Text generation
async function generateSingleElement(element: AdMediaElement) {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  // Generate texts
  const { data } = await AdsApi.generateTextForMediaElement(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    { element },
  );

  return data.payload;
}

const isGenerateAllDisabled = computed(
  () => !values.elements?.every((element) => !!element.intention),
);

async function handleGenerateAllTexts() {
  if (!values.elements) return;

  try {
    isGeneratingAllTexts.value = true;
    generalErrorMessage.value = undefined;

    if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
      throw new UnidentifiedError();
    }

    // Generate texts
    const { data: response } = await AdsApi.generateTextsForMediaElements(
      store.brandId,
      store.campaignId,
      store.currentAd.ad_id,
      store.currentChannel.channel_id,
      store.currentVariant.id,
      {
        elements: values.elements,
      },
    );

    bulkGeneratedSlices.value = response
      .map((element) => element.payload)
      .map((payload) => (typeof payload === "string" ? [payload] : payload));
  } catch (e: unknown) {
    console.error(e);

    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.generate-text-error",
    );
  } finally {
    isGeneratingAllTexts.value = false;
  }
}
//#endregion

const isDisabled = computed(
  () => isSubmitting.value || isGeneratingAllTexts.value,
);
</script>

<template>
  <!-- The content grows, so the footer stays at the bottom of the screen -->
  <form class="tw:flex tw:grow tw:flex-col" @submit.prevent="onSubmit">
    <Container :maxWidth="1088" class="tw:grow tw:py-8">
      <div class="tw:flex tw:flex-col tw:items-start tw:gap-16 tw:lg:flex-row">
        <div class="tw:grid tw:w-full tw:grid-cols-1 tw:gap-6">
          <AdsAssemblyEditorOverlayAbyssaleAlerts />

          <AdMediaElementField
            v-for="(element, index) in values.elements"
            :key="element.name"
            :name="`elements[${index}]`"
            :generateFn="generateSingleElement"
            :bulkGeneratedTexts="bulkGeneratedSlices[index]"
            :disabled="isDisabled"
          />

          <Separator />

          <Alert v-if="generalErrorMessage" type="error" autoScroll>
            {{ generalErrorMessage }}
          </Alert>

          <div
            class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:md:flex-row"
          >
            <p class="tw:text-sm tw:text-secondary-text">
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.generate-all-copies-hint",
                )
              }}
            </p>

            <Button
              size="md"
              type="button"
              leftIcon="custom:hi-luca"
              class="tw:whitespace-nowrap"
              :disabled="isGenerateAllDisabled"
              :isLoading="isGeneratingAllTexts"
              @click="handleGenerateAllTexts"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.generate-all-copies",
                )
              }}
            </Button>
          </div>
        </div>

        <AdsAssemblyEditorOverlayPreviewTemplate
          @openPreview="isPreviewOpen = true"
        />
      </div>
    </Container>

    <AdsAssemblyEditorOverlayFooter>
      <Button variant="label" :isLoading="isSubmitting">
        {{ $t("funnel-flow.paid-social.ads.refine.editor.save-changes") }}
      </Button>

      <Button
        :isLoading="isSubmitting || isWaitingForAbyssale"
        @click="generatePreviews = true"
      >
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.save-generate-preview")
        }}
      </Button>
    </AdsAssemblyEditorOverlayFooter>

    <!-- Save locking -->
    <ModalFormSaveOrDiscard
      :isDirty="meta.dirty && !submitSuccess"
      :saveFn="handleSaveAndExit"
    >
      <template #description>
        {{ $t("funnel-flow.paid-social.ads.refine.editor.pending-changes") }}
      </template>
    </ModalFormSaveOrDiscard>

    <!-- Preview modal displayed after submitting -->
    <AdFormatsPreviewModal
      v-if="store.currentSet && store.currentAd && store.currentVariant"
      v-model="isPreviewOpen"
      :adSetName="store.currentSet.name"
      :adName="store.currentAd.ad_name"
      :formats="store.currentVariant.media.formats ?? []"
    />
  </form>
</template>
