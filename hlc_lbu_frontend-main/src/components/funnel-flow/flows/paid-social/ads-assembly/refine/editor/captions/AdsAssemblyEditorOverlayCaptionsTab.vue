<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdChannelAttribute,
  AdChannelAttributePayload,
  AdChannelAttributeType,
  adChannelAttributeTypes,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, number, object, string } from "yup";

const props = defineProps<{ attributeName: string }>();

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

// Video ads show their video in the preview instead of the banner
const { src: videoSrc, refresh: refreshVideoSrc } = useStoredFileSrc(() => {
  const video = store.getCurrentAdVariantVideo(store.currentVariant?.id);
  return { storage_key: video?.storage_key, storage_url: video?.storage_path };
});

const isPreviewOpen = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      attribute: object({
        id: number().required(),
        max: number().required(),
        min: number().required(),
        name: string().required(),
        type: mixed<AdChannelAttributeType>()
          .oneOf(adChannelAttributeTypes)
          .required(),
        max_char: number().required(),
        payloads: array()
          .of(
            object({
              id: number().required(t("forms.required-field")),
              payload: string()
                .required(t("forms.required-field"))
                .trim()
                // Check max characters
                .test("maxCharacters", (value, context) => {
                  const maxCharacters = context.from?.[1]?.value?.max_char;

                  if (maxCharacters && value.length > maxCharacters) {
                    return context.createError({
                      message: t("forms.max-characters", {
                        max: maxCharacters,
                      }),
                    });
                  }

                  return true;
                }),
            }),
          )
          .required(),
        display_name: string().required(),
      }),
    }).required(),
  ),
);

// Find the attribute
const initialAttribute = store.currentVariant?.channel_attributes?.find(
  (attribute) => attribute.name === props.attributeName,
);

// Format the initial form values
const initialValues = {
  ...initialAttribute,
  payloads:
    initialAttribute?.payloads.filter(
      (payload): payload is AdChannelAttributePayload => Boolean(payload),
    ) ?? [],
};

// If there are no payloads, initialize with an empty one
if (initialValues?.payloads.length === 0) {
  // @ts-expect-error Payload should be initialized to undefined
  initialValues.payloads.push({ id: 0, payload: undefined });
}

const { handleSubmit, isSubmitting, meta, submitSuccess, values } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      attribute: initialValues,
    },
    validateOnMount: true,
  });

async function save() {
  if (
    !store.currentAd ||
    !store.currentChannel ||
    !store.currentVariant ||
    !initialAttribute
  ) {
    throw new UnidentifiedError();
  }

  // Map the whole array of attributes
  const attributes =
    store.currentVariant.channel_attributes?.map<AdChannelAttribute>(
      (attribute) => {
        return attribute.name === props.attributeName && values.attribute
          ? (values.attribute as AdChannelAttribute)
          : attribute;
      },
    ) ?? [];

  // Save the array
  await AdsApi.saveAdChannelAttributes(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    { attributes: attributes },
  );

  // Refetch the ad
  await store.refetchCurrentAd();

  // Revalidate funnel flow
  await paidSocialFormStore.revalidate();

  await sleep(500);
}

const onSubmit = handleSubmit(async (_values) => {
  await save();
});

async function handleSaveAndExit() {
  await save();
}

// Create a copy of the variant that includes the edited payloads to pass down to the preview
const adVariantForPreview = computed(() =>
  store.currentVariant
    ? {
        ...store.currentVariant,
        channel_attributes:
          store.currentVariant?.channel_attributes?.map((attribute) =>
            attribute.name === props.attributeName
              ? { ...attribute, payloads: values.attribute?.payloads ?? [] }
              : attribute,
          ) ?? [],
      }
    : undefined,
);
</script>

<template>
  <!-- The content grows, so the footer stays at the bottom of the screen -->
  <form class="tw:flex tw:grow tw:flex-col" @submit.prevent="onSubmit">
    <Container :maxWidth="1088" class="tw:grow tw:py-8">
      <div class="tw:flex tw:flex-col tw:items-start tw:gap-16 tw:lg:flex-row">
        <div class="tw:grid tw:w-full tw:grid-cols-1 tw:gap-6">
          <AdChannelAttributeFieldList
            name="attribute"
            :disabled="isSubmitting"
          />
        </div>

        <AdsAssemblyEditorOverlayPreviewTemplate
          @openPreview="isPreviewOpen = true"
        >
          <AdPreviewFromData
            v-if="adVariantForPreview"
            :media="adVariantForPreview.media"
            :channel_attributes="adVariantForPreview.channel_attributes"
            :videoSrc="videoSrc"
            :aspectRatio="store.isCurrentSetVideoFormat ? 'auto' : undefined"
            size="lg"
            @videoError="refreshVideoSrc"
          />
        </AdsAssemblyEditorOverlayPreviewTemplate>
      </div>
    </Container>

    <AdsAssemblyEditorOverlayFooter>
      <Button variant="label" :uppercase="false" :isLoading="isSubmitting">
        {{ $t("funnel-flow.paid-social.ads.refine.editor.save-changes") }}
      </Button>

      <Button :uppercase="false" :isLoading="isSubmitting">
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
    <AdsAssemblyEditorOverlayCaptionsPreviewModal v-model="isPreviewOpen" />
  </form>
</template>
