<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdVariant,
  doesVariantHavePinnedFormat,
  doesVariantHaveValidAttributes,
  doesVariantHaveValidMedia,
  isVariantCompleted,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { number, object, string } from "yup";
import { AdsAssemblyCreativeDirectionModalMode } from "./AdsAssemblyCreativeDirectionModal.vue";
import Alert from "@/components/alerts/Alert.vue";

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

// This screen is also the last step of the video flow. The variants show their
// video instead of the banner, the editor only edits the captions, and the
// image-only actions (creative direction, deleting, adding variants) are hidden
const isVideo = computed(() => store.isCurrentSetVideoFormat);

const showDeleteConfirmModal = ref(false);
const isEditorOpen = ref(false);
const selectedVariantToDelete = ref<AdVariant | undefined>(undefined);

const isCreativeDirectionModalOpen = ref(false);
const creativeDirectionModalMode =
  ref<AdsAssemblyCreativeDirectionModalMode>("editSingle");
const creativeDirectionVariant = ref<AdVariant | undefined>(undefined);
const isMoveForwardModalOpen = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string()
        .required(t("forms.required-field"))
        .max(META_ADS_MAX_NAME_LENGTH, ({ max }) =>
          t("forms.max-characters", { max }),
        )
        .trim(),
      selectedId: number().required(
        t("funnel-flow.paid-social.ads.refine.select-variation"),
      ),
      url: string()
        .required(t("forms.required-field"))
        .url(t("forms.url-invalid")),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  values,
  setFieldValue,
  isFieldDirty,
  errors,
  submitCount,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  resetDirtyOnSubmit: true,
  initialValues: {
    name: store.currentAd?.ad_name,
    selectedId: store.currentChannel?.variants.find(
      (variant) => variant.selected,
    )?.id,
    url: store.currentAd?.url ?? undefined,
  },
});

const alertRef = ref<InstanceType<typeof Alert>>();

const selectedVariant = computed<AdVariant | undefined>(() =>
  store.currentChannel?.variants.find(
    (variant) => variant.id === values.selectedId,
  ),
);

// `null` is a video variant without its video yet, `undefined` an image variant
const selectedVariantVideo = computed(() =>
  isVideo.value
    ? (store.getCurrentAdVariantVideo(selectedVariant.value?.id) ?? null)
    : undefined,
);

const isSelectedVariantValid = computed(() =>
  isVariantCompleted(selectedVariant.value, selectedVariantVideo.value),
);

const hasTextOrMediaIssue = computed(() => {
  if (!doesVariantHaveValidAttributes(selectedVariant.value)) return true;

  // A video variant has no banner to check
  if (isVideo.value) return false;

  return !doesVariantHaveValidMedia(selectedVariant.value);
});

const hasNoPinnedFormat = computed(
  () => !isVideo.value && !doesVariantHavePinnedFormat(selectedVariant.value),
);

async function save() {
  if (!store.currentAd || !store.currentChannel) {
    throw new UnidentifiedError();
  }

  // Save name
  if (values.name && isFieldDirty("name")) {
    await AdsApi.setAdName({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: store.currentAd?.ad_id,
      name: values.name,
    });
  }

  // Save redirect url
  if (values.url && isFieldDirty("url")) {
    await AdsApi.setAdRedirectUrl({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: store.currentAd.ad_id,
      redirect_url: values.url,
    });
  }

  // Set selected ad
  if (values.selectedId !== undefined && isFieldDirty("selectedId")) {
    await AdsApi.selectAdVariant({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: store.currentAd.ad_id,
      channel_id: store.currentChannel.channel_id,
      variant_id: values.selectedId,
    });
  }

  await store.refetchCurrentAd();

  // Revalidate funnel flow
  await paidSocialFormStore.revalidate();

  // Scroll to alert if it's present
  if (!isSelectedVariantValid.value) {
    await alertRef.value?.scroll();
  }

  await sleep(1000);
}

const onSubmit = handleSubmit(async () => {
  await save();

  if (store.currentAd && store.isAdCompleted(store.currentAd)) {
    isMoveForwardModalOpen.value = true;
  }
});

function handleGoBack() {
  if (isVideo.value) {
    store.setPreviousVideoScreen("videoAd");
  } else {
    store.setScreen("settings");
  }
}

function handleRegenerateAllSets() {
  creativeDirectionModalMode.value = "generateList";
  creativeDirectionVariant.value = undefined;
  isCreativeDirectionModalOpen.value = true;
}

function handleAddAds() {
  creativeDirectionModalMode.value = "generateSingle";
  creativeDirectionVariant.value = undefined;
  isCreativeDirectionModalOpen.value = true;
}

function handleCreativeDirection(variant: AdVariant) {
  creativeDirectionModalMode.value = "editSingle";
  creativeDirectionVariant.value = variant;
  isCreativeDirectionModalOpen.value = true;
}

function handleDelete(variant: AdVariant) {
  selectedVariantToDelete.value = variant;
  showDeleteConfirmModal.value = true;
}

function handleEditVariant(variant: AdVariant) {
  store.setCurrentVariantId(variant.id);
  isEditorOpen.value = true;
}

const handleConfirmDelete = async () => {
  if (
    !selectedVariantToDelete.value ||
    !store.currentSet ||
    !store.currentChannel
  ) {
    throw new UnidentifiedError();
  }

  await AdsApi.deleteAdVariant({
    brand_id: store.brandId,
    campaign_id: store.campaignId,
    ad_set_id: store.currentSet.id,
    channel_id: store.currentChannel.channel_id,
    variant_id: selectedVariantToDelete.value.id,
  });

  await store.refetchCurrentAd();

  // Unselect the variant if it was selected
  if (selectedVariantToDelete.value.id === values.selectedId) {
    setFieldValue("selectedId", undefined);
  }
};

// Pool constantly to update the visuals:
// If the ad is still being generated, we want to update the visuals as soon as they are ready
// If a visual was edited in abbysale, we want to update the visuals as soon as they are ready
// Video ads have no visuals generated in Abyssale, so they don't need it
useIntervalFn(
  async () => {
    if (isVideo.value) return;

    await store.refetchCurrentAd();
  },
  () => 10 * SECOND_IN_MS,
  { immediate: true },
);
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :maxWidth="910">
    <template #stepper>
      <AdsAssemblyVideoStepper v-if="isVideo" />
      <AdsAssemblyImageStepper v-else />
    </template>

    <!-- TODO: add the help video URL of the video flow later -->
    <PageTitle
      helpButton
      :helpVideoUrl="
        isVideo ? undefined : 'https://www.youtube.com/watch?v=r1462xlXJOQ'
      "
    >
      {{
        $t(
          isVideo
            ? "funnel-flow.paid-social.ads.video.ad.title"
            : "funnel-flow.paid-social.ads.refine.title",
        )
      }}

      <template #description>
        {{
          $t(
            isVideo
              ? "funnel-flow.paid-social.ads.video.ad.description"
              : "funnel-flow.paid-social.ads.refine.description",
            {
              count: store.currentSet?.ads.length,
            },
          )
        }}
      </template>

      <template #after>
        <AdsAssemblyAbyssaleLinkButton v-if="!isVideo" />
      </template>
    </PageTitle>

    <CardBase
      v-if="store.currentSet && store.currentAd"
      class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6"
      :disabled="isSubmitting"
    >
      <div
        class="tw:flex tw:flex-col tw:gap-4 tw:xl:flex-row tw:xl:items-center"
      >
        <FieldEditableText
          name="name"
          required
          class="name-field tw:grow"
          variant="text"
          type="textarea"
        />

        <Button
          v-if="!isVideo"
          type="button"
          leftIcon="tabler:plus"
          variant="label"
          size="sm"
          class="tw:whitespace-nowrap"
          :uppercase="false"
          @click="handleRegenerateAllSets"
        >
          {{ $t("funnel-flow.paid-social.ads.refine.regenerate-all-sets") }}
        </Button>
      </div>

      <Alert
        v-if="selectedVariant && !isSelectedVariantValid"
        ref="alertRef"
        type="warning"
      >
        <template #title>
          {{
            $t("funnel-flow.paid-social.ads.refine.variant-invalid-alert.title")
          }}
        </template>

        <template #custom>
          <ul class="tw:list-disc tw:space-y-1 tw:pl-5 tw:font-normal">
            <li v-if="hasTextOrMediaIssue">
              <i18n-t
                keypath="funnel-flow.paid-social.ads.refine.variant-invalid-alert.text-limits"
                tag="span"
              >
                <template #editDetails>
                  <span class="tw:font-bold">
                    {{ $t("funnel-flow.paid-social.ads.refine.edit-details") }}
                  </span>
                </template>
              </i18n-t>
            </li>

            <li v-if="hasNoPinnedFormat">
              <i18n-t
                keypath="funnel-flow.paid-social.ads.refine.variant-invalid-alert.no-pinned-asset"
                tag="span"
              >
                <template #editDetails>
                  <span class="tw:font-bold">
                    {{ $t("funnel-flow.paid-social.ads.refine.edit-details") }}
                  </span>
                </template>
              </i18n-t>
            </li>

            <li v-if="selectedVariantVideo === null">
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.variant-invalid-alert.no-video",
                )
              }}
            </li>
          </ul>
        </template>
      </Alert>

      <Separator />

      <div
        class="tw:grid tw:grid-cols-1 tw:items-start tw:gap-4 tw:xl:grid-cols-3"
      >
        <AdsAssemblyRefineAdCard
          v-if="store.currentAd"
          v-for="variant in store.currentChannel?.variants"
          :ad="store.currentAd"
          :adVariant="variant"
          :isVideo="isVideo"
          :video="store.getCurrentAdVariantVideo(variant.id)"
          :selected="values.selectedId === variant.id"
          :hasError="submitCount > 0 && !!errors.selectedId"
          style="min-height: 342px"
          :class="{
            'tw:opacity-50':
              values.selectedId !== undefined &&
              values.selectedId !== variant.id,
          }"
          @delete="handleDelete(variant)"
          @edit="handleEditVariant"
          @creativeDirection="handleCreativeDirection"
          @select="setFieldValue('selectedId', variant.id)"
        />

        <CardBase
          v-if="
            !isVideo &&
            (!store.currentChannel || store.currentChannel.variants.length < 3)
          "
          is="button"
          type="button"
          color="secondary"
          class="tw:flex tw:items-center tw:justify-center tw:gap-2 tw:text-gray-600"
          :class="{
            'tw:xl:aspect-auto':
              store.currentChannel && store.currentChannel.variants.length > 0,
          }"
          style="min-height: 413px"
          @click="handleAddAds"
        >
          <Icon icon="custom:hi-luca" class="tw:text-xl" />
          <span class="tw:text-sm tw:font-medium">
            {{ $t("funnel-flow.paid-social.ads.refine.add-ads") }}
          </span>
        </CardBase>
      </div>

      <FieldError
        v-if="submitCount > 0 && errors.selectedId"
        data-error-scroll-target="selectedId"
        disableMargin
      >
        {{ errors.selectedId }}
      </FieldError>
    </CardBase>

    <CardBase :disabled="isSubmitting" class="tw:p-6">
      <FieldText
        name="url"
        :label="$t('funnel-flow.paid-social.ads.refine.proposed-url.label')"
        :placeholder="
          $t('funnel-flow.paid-social.ads.refine.proposed-url.placeholder')
        "
        required
      >
        <template #hint>
          {{ $t("funnel-flow.paid-social.ads.refine.proposed-url.hint") }}
        </template>
      </FieldText>
    </CardBase>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="handleGoBack" />

        <Button
          :uppercase="false"
          icon="tabler:arrow-right"
          :isLoading="isSubmitting"
        >
          <template v-if="store.nextAd">
            {{ $t("funnel-flow.paid-social.ads.refine.save-next-ad") }}
          </template>
          <template v-else>
            {{ $t("funnel-flow.paid-social.ads.refine.save-summary") }}
          </template>
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <AdsAssemblyAdDeleteModal
    v-if="showDeleteConfirmModal"
    v-model="showDeleteConfirmModal"
    :confirmFn="handleConfirmDelete"
  />

  <AdsAssemblyCreativeDirectionModal
    v-if="isCreativeDirectionModalOpen && store.currentAd"
    v-model="isCreativeDirectionModalOpen"
    :ad="store.currentAd"
    :mode="creativeDirectionModalMode"
    :variant="creativeDirectionVariant"
  />

  <AdsAssemblyRefineMoveForwardModal v-model="isMoveForwardModalOpen" />

  <AdsAssemblyEditorOverlay v-if="isEditorOpen" v-model="isEditorOpen" />
</template>

<style scoped>
@reference "#styles/main.css";

.name-field {
  @apply tw:text-xl tw:font-bold!;

  :deep(.v-field__input) {
    @apply tw:text-xl tw:font-bold;
  }
}
</style>
