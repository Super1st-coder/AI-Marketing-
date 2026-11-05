<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object, string } from "yup";
import AdsApi, {
  AdByCampaignDefinitionData,
  AdVariant,
} from "@/services/funnel-flow/paid-social/AdsApi";
import {
  InsufficientCreditsError,
  UnidentifiedError,
} from "@/services/common-errors";
import {
  creditsRefusalFromJob,
  videoCreditsErrorKey,
} from "@/composables/useVideoCredits";
import AdStructureApi, {
  isGenerateAdVariationsJobFinished,
} from "@/services/funnel-flow/paid-social/AdStructureApi";

export type AdsAssemblyCreativeDirectionModalMode =
  "generateList" | "generateSingle" | "editSingle";

const props = defineProps<{
  ad: AdByCampaignDefinitionData;
  mode: AdsAssemblyCreativeDirectionModalMode;
  variant?: AdVariant;
}>();

const isOpen = defineModel<boolean>({ required: true });

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();

const generalErrorMessage = ref<string | undefined>(undefined);

// Luca Credits (Gate 2), same as the video flow: a refusal for lack of credits gets its own
// message and an "Add credits" button instead of the generic AI error
const { refresh: refreshCredits } = useVideoCredits();
const isOutOfCredits = ref(false);
const isAddCreditsOpen = ref(false);
// Luca Credits isn't released in production yet: only where the video flow is on
const showsCredits = IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT;

// Number of variants the "generateList" mode can request, with the trade-off
// shown next to each one
const variantCountChoices = [
  { count: 1, descriptionKey: "fastest" },
  { count: 2, descriptionKey: "balanced" },
  { count: 3, descriptionKey: "most-diversity" },
] as const;

const variantCountOptions = computed(() =>
  variantCountChoices.map((choice) => ({
    value: choice.count,
    label: t(
      "funnel-flow.paid-social.ads.refine.creative-direction.variant-count.option",
      { count: choice.count },
    ),
  })),
);

function getVariantCountDescription(count: unknown) {
  const choice = variantCountChoices.find((c) => c.count === count);

  return choice
    ? t(
        `funnel-flow.paid-social.ads.refine.creative-direction.variant-count.descriptions.${choice.descriptionKey}`,
      )
    : "";
}

const schema = computed(() =>
  toTypedSchema(
    object({
      text: string().required().trim(),
      variantCount: number()
        .oneOf(variantCountChoices.map((choice) => choice.count))
        .required(),
    }).required(),
  ),
);

const { handleSubmit, isSubmitting, values } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    text: undefined,
    variantCount: 1,
  },
});

const onSubmit = handleSubmit(async (values) => {
  try {
    generalErrorMessage.value = undefined;
    isOutOfCredits.value = false;

    if (!store.currentAd || !store.currentChannel) {
      throw new UnidentifiedError();
    }

    let jobId: string;

    // Start job
    if (props.mode === "editSingle") {
      // Edit the current variant with a custom prompt.

      // The variant is required in this mode
      if (!props.variant) {
        throw new UnidentifiedError();
      }

      const response = await AdsApi.startGenerateSingleAdVariantJob({
        brand_id: store.brandId,
        campaign_id: store.campaignId,
        ad_id: store.currentAd.ad_id,
        channel_id: store.currentChannel.channel_id,
        variant_id: props.variant.id,
        add_variant: true,
        custom_prompt: values.text,
      });

      jobId = response.data.job_id;
    } else if (props.mode === "generateSingle") {
      // Generate a new single variant

      const response = await AdsApi.startGenerateSingleAdVariantJob({
        brand_id: store.brandId,
        campaign_id: store.campaignId,
        ad_id: store.currentAd.ad_id,
        channel_id: store.currentChannel.channel_id,
        variant_id: null,
        add_variant: true,
        custom_prompt: values.text,
      });

      jobId = response.data.job_id;
    } else {
      // Generate a new list with the selected number of variants
      const response = await AdsApi.startGenerateAdVariantListJob({
        brand_id: store.brandId,
        campaign_id: store.campaignId,
        ad_id: store.currentAd.ad_id,
        channel_id: store.currentChannel.channel_id,
        add_variant: true,
        custom_prompt: values.text,
        n_variants: values.variantCount,
      });

      jobId = response.data.job_id;
    }

    // Start a pooling process to wait for the final response or error
    const result = await pooling(
      async () => {
        const { data: response } =
          await AdStructureApi.getGenerateAdVariationsJobResult(jobId);

        return response;
      },
      (response) => isGenerateAdVariationsJobFinished(response),
      ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_POLLING_INTERVAL_MS,
      { timeoutMs: ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_TIMEOUT_MS },
    );

    // Refused by Luca Credits inside the job: handled below like a refused start
    const refusal = creditsRefusalFromJob(result);
    if (refusal) throw refusal;

    if (result.status === "FAILED") {
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.ads.refine.creative-direction.ai-generation-error",
      );
      return;
    }

    // The job was successfull, refetch the the whole ad
    await store.refetchCurrentAd();
    // It charged credits: keep the counter current
    if (showsCredits) void refreshCredits();

    // Close the modal
    isOpen.value = false;
  } catch (e: unknown) {
    console.error(e);

    // Out of credits / billing down get their own message, as in the video flow
    const billingKey = videoCreditsErrorKey(e);
    if (billingKey && showsCredits) void refreshCredits();
    isOutOfCredits.value =
      showsCredits && e instanceof InsufficientCreditsError;
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.refine.creative-direction.ai-generation-error",
    );
  }
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="800"
    v-slot="{ close }"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{
        $t("funnel-flow.paid-social.ads.refine.creative-direction.title", {
          adName: ad.ad_name,
        })
      }}

      <template #description>
        {{
          mode === "generateList"
            ? $t(
                "funnel-flow.paid-social.ads.refine.creative-direction.description-list",
              )
            : $t(
                "funnel-flow.paid-social.ads.refine.creative-direction.description-single",
              )
        }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:grid tw:grid-cols-1 tw:gap-6">
      <FieldNewSelect
        v-if="mode === 'generateList'"
        name="variantCount"
        :label="
          $t(
            'funnel-flow.paid-social.ads.refine.creative-direction.variant-count.label',
          )
        "
        :options="variantCountOptions"
        :clearable="false"
        :disabled="isSubmitting"
        chips
      >
        <template #chip>
          <span class="tw:line-clamp-1">
            <span class="tw:text-primary-text">
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.creative-direction.variant-count.option",
                  { count: values.variantCount },
                )
              }}
            </span>
            {{ " " }}
            <span class="tw:text-gray-500">
              {{ getVariantCountDescription(values.variantCount) }}
            </span>
          </span>
        </template>

        <template #item="{ props: itemProps, item }">
          <VListItem v-bind="itemProps">
            <template #title>
              <span class="tw:text-primary-text">{{ item.label }}</span>
              {{ " " }}
              <span class="tw:text-gray-500">
                {{ getVariantCountDescription(item.value) }}
              </span>
            </template>
          </VListItem>
        </template>
      </FieldNewSelect>

      <FieldTextarea
        name="text"
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.refine.creative-direction.placeholder',
          )
        "
        :rows="4"
        :disabled="isSubmitting"
        speechRecognition
      />

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}

        <template v-if="isOutOfCredits" #actions>
          <Button
            size="sm"
            leftIcon="tabler:shopping-cart"
            data-testid="creative-direction-add-credits"
            @click="isAddCreditsOpen = true"
          >
            {{
              $t("funnel-flow.paid-social.ads.video.credits.add-credits.button")
            }}
          </Button>
        </template>
      </Alert>

      <AdsAssemblyVideoAddCreditsModal
        v-if="showsCredits"
        v-model="isAddCreditsOpen"
      />
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        type="button"
        :uppercase="false"
        @click="close"
        :disabled="isSubmitting"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="submit" :uppercase="false" :isLoading="isSubmitting">
        {{
          mode === "generateList"
            ? $t(
                "funnel-flow.paid-social.ads.refine.creative-direction.generate-variations",
                { count: values.variantCount },
              )
            : $t(
                "funnel-flow.paid-social.ads.refine.creative-direction.generate",
              )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
