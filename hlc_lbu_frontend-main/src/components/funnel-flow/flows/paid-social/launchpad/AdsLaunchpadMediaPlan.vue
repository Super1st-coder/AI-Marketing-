<script setup lang="ts">
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";
import AdsApi, {
  AdChannelDefinition,
  AdMediaFormat,
  getChannelSelectedVariant,
} from "@/services/funnel-flow/paid-social/AdsApi";
import AudienceApi from "@/services/projects/AudienceApi";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";
import CampaignsApi from "@/services/projects/CampaignsApi";

const { goBack, goNext } = useMultiStepFormContext();

const { data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();
const projectId = useProjectId();

const modalFormats = ref(false);
const formats = ref<AdMediaFormat[]>([]);
const adsetNameRef = ref<string>("");
const adNameRef = ref<string>("");

// Fetch ad structure
const { data: adStructure } = await AdStructureApi.getAdStructureByChannelGroup(
  brandId,
  campaignId,
  data.value.channelGroupId,
);

// Fetch the ads
const ads = await Promise.all(
  adStructure.ad_sets.map(
    async (set) =>
      await Promise.all(
        set.ads.map(
          async (ad) =>
            (await AdsApi.getOneAd(brandId, campaignId, ad.id)).data,
        ),
      ),
  ),
);

// Fetch the audiences of all sets
const [audiences, experiments] = await Promise.all([
  await Promise.all(
    adStructure.ad_sets.map(
      async (set) =>
        (await AudienceApi.GetAudiencesByAdSet(brandId, campaignId, set.id))
          .data.audiences,
    ),
  ),
  await Promise.all(
    adStructure.ad_sets.map(
      async (set) =>
        (await AdsExperiment.getExperimentByAdSet(brandId, campaignId, set.id))
          .data,
    ),
  ),
]);

const { data: campaign } = await CampaignsApi.getOne(
  brandId,
  projectId,
  campaignId,
);

const joinedData = computed(() =>
  adStructure.ad_sets.map((set, index) => ({
    ...set,
    audiences: audiences[index],
    experiment: experiments[index],
    ads: ads[index],
  })),
);

function getChannel(
  channel: AdChannelDefinition,
  adSetName: string,
  adName: string,
) {
  modalFormats.value = true;
  formats.value = getChannelSelectedVariant(channel)!.media.formats!;
  adsetNameRef.value = adSetName;
  adNameRef.value = adName;
}
</script>

<template>
  <FormStepLayout>
    <!-- Horizontal Stepper -->
    <template #stepper>
      <AdsLaunchpadStepper />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=PS-LLZhhrJA"
    >
      {{ $t("funnel-flow.paid-social.launchpad.media-plan.title") }}
      <template #description>
        {{ $t("funnel-flow.paid-social.launchpad.media-plan.description") }}
      </template>
    </PageTitle>

    <AdsLaunchpadCampaignHeader :campaign="campaign">
      <AdsLaunchpadCampaignHeaderMediaPlan :campaign="campaign" />
    </AdsLaunchpadCampaignHeader>

    <AdsetsSummary :joinedData="joinedData" @get-channel="getChannel" />

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <PermissionGuard
          :requires="[{ name: 'CAMPAIGN_LAUNCHPAD', actions: ['C', 'U'] }]"
        >
          <Button type="button" @click="goNext">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.media-plan.next-step-technical-configuration",
              )
            }}
          </Button>
        </PermissionGuard>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <AdFormatsPreviewModal
    :adSetName="adsetNameRef"
    :adName="adNameRef"
    :formats="formats"
    v-model="modalFormats"
  />
</template>
