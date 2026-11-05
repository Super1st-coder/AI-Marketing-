<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import CampaignsApi, {
  CampaignChannelGroupData,
  CampaignData,
} from "@/services/projects/CampaignsApi";
import FunnelFlowApi from "@/services/funnel-flow/FunnelFlowApi";
import { FunnelFlowValidatorStateError } from "@/services/funnel-flow/FunnelFlowValidatorApi";
import { useRouteQuery } from "@vueuse/router";
import { useI18n } from "vue-i18n";

export type FunnelPaidSocialFormData = {
  funnelFlowId: number;
  channelGroupId: number;
  channelGroup: CampaignChannelGroupData;
  campaign: CampaignData;
};

const props = defineProps<{
  data?: FunnelPaidSocialFormData;
}>();

const { t, te } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const targetInitialStep = useRouteQuery<string, string | undefined>(
  "initialStep",
  undefined,
);

// Get campaign
const { data: campaign } = await CampaignsApi.getOne(
  brandId,
  projectId,
  campaignId,
);

// Initialize store
const store = useFunnelPaidSocialFormStore();
await store.initialize(campaign);

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();
preCheckStore.clear();

// A published campaign loads its launchpad from the publish endpoint, so the
// pre-check does not need to be run again and the summary can be shown directly
try {
  await preCheckStore.initializeFromPublished(projectId, brandId, campaignId);
} catch (error) {
  console.error("Failed to load the published campaign:", error);
  preCheckStore.clearPrecheck();
}

const isLaunchpadStep = (name?: string) =>
  name?.startsWith("launchpad") ?? false;

// Fetch funnel flows in the campaign
const { data: funnelFlows } = await FunnelFlowApi.getFunnelFlowListByCampaign(
  brandId,
  campaignId,
);

// Find the Paid Social funnel flow
const paidSocialFunnel = funnelFlows.funnel_flows.find(
  (flow) => flow.channel_group_name === PAID_SOCIAL_CHANNEL_GROUP_NAME,
);

// If the paid social funnel flow is not found, throw an error
if (!paidSocialFunnel) {
  throw new UnidentifiedError();
}

// Fetch channel group data from the funnel flow
const { data: channelGroupList } = await AdStructureApi.getChannelGroupList(
  brandId,
  campaignId,
);

// Find the channel group data from the funnel flow
const channelGroup = channelGroupList.channel_group.find(
  (group) => group.id === paidSocialFunnel.channel_group_id,
);

// If the channel group data is not found, throw an error
if (!channelGroup) {
  throw new UnidentifiedError();
}

const shouldBackToCampaign = shouldAutoRedirectFromFunnelFlowHome(
  channelGroupList.channel_group,
);

const authStore = useAuthStore();

const userHas = (step: FormStep<FunnelPaidSocialFormData>) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep<FunnelPaidSocialFormData>[]>(() => [
  {
    name: "channel",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.channel"),
    icon: "tabler:template",
    requires: [{ name: "FUNNEL_FLOW", actions: ["C", "U", "R"] }],
    next: () => getStepEntry("ads_structure"),
    disabled: () => store.isStepDisabled("channel"),
    hasAlert: () => store.doesStepHaveAlert("channel"),
    hasTooltip: () => store.doesStepHaveAlert("channel"),
  },
  {
    name: "ads_structure",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.structure"),
    icon: "tabler:ruler-2",
    requires: [{ name: "FUNNEL_FLOW", actions: ["C", "U", "R"] }],
    children: [
      { name: "structureTutorial" },
      { name: "structureSelection" },
      { name: "structure" },
    ],
    disabled: () => store.isStepDisabled("ads_structure"),
    hasAlert: () => store.doesStepHaveAlert("ads_structure"),
    hasTooltip: () => store.doesStepHaveAlert("ads_structure"),
  },
  {
    name: "audiences",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.audience"),
    icon: "ic:round-people-alt",
    requires: [{ name: "FUNNEL_FLOW", actions: ["C", "U", "R"] }],
    disabled: () => store.isStepDisabled("audiences"),
    hasAlert: () => store.doesStepHaveAlert("audiences"),
    hasTooltip: () => store.doesStepHaveAlert("audiences"),
  },
  {
    name: "ads_experiment",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.ads-experiment"),
    icon: "tabler:layout-2",
    requires: [{ name: "FUNNEL_FLOW", actions: ["C", "U", "R"] }],
    next: () => getStepEntry("ads"),
    disabled: () => store.isStepDisabled("ads_experiment"),
    hasAlert: () => store.doesStepHaveAlert("ads_experiment"),
    hasTooltip: () => store.doesStepHaveAlert("ads_experiment"),
  },
  {
    name: "ads",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.ads"),
    icon: "tabler:layout-navbar",
    requires: [{ name: "FUNNEL_FLOW", actions: ["C", "U", "R"] }],
    children: [{ name: "adsAssemblyTutorial" }, { name: "adsAssembly" }],
    disabled: () => store.isStepDisabled("ads"),
    hasAlert: () => store.doesStepHaveAlert("ads"),
    hasTooltip: () => store.doesStepHaveAlert("ads"),
  },
  {
    name: "summary",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.summary"),
    icon: "tabler:layout-navbar",
    requires: [{ name: "FUNNEL_FLOW", actions: ["R"] }],
    next: () => getStepEntry("launchpad"),
    disabled: () => store.isStepDisabled("summary"),
    hasAlert: () => store.doesStepHaveAlert("summary"),
    hasTooltip: () => store.doesStepHaveAlert("summary"),
  },
  // Review step hidden for now
  // {
  //   name: "review",
  //   label: t("funnel-flow.paid-social.sidebar-menu.steps.review"),
  //   icon: "tabler-file-text",
  //   requires: [{ name: "FUNNEL_FLOW", actions: ["R"] }],
  //   children: [{ name: "review" }, { name: "attachments" }],
  //   disabled: () => store.isStepDisabled("review"),
  //   hasAlert: () => store.doesStepHaveAlert("review"),
  //   hasTooltip: () => store.doesStepHaveAlert("review"),
  // },
  {
    name: "launchpad",
    label: t("funnel-flow.paid-social.sidebar-menu.steps.publish-to-channel"),
    icon: "tabler:message-2-up",
    requires: [{ name: "FUNNEL_FLOW", actions: ["R"] }],
    children: [
      { name: "launchpadTutorial" },
      { name: "launchpadReviewCampaign" },
      { name: "launchpadMediaPlan" },
      { name: "launchpadTechnicalConfig" },
      { name: "launchpadPreCheck" },
      { name: "launchpadSummary" },
    ],
    disabled: () => store.isStepDisabled("launchpad"),
    hasAlert: () => store.doesStepHaveAlert("launchpad"),
    hasTooltip: () => store.doesStepHaveAlert("launchpad"),
  },
]);

// Map validator steps to their corresponding form step names
const validatorStepToFormStepMap: Record<string, string> = {
  channel: "channel",
  ads_structure: "ads_structure",
  audiences: "audiences",
  ads_experiment: "ads_experiment",
  ads: "ads",
};

// Resolve which child a step with children opens on, skipping its tutorial
// when the user opted out of it or already has progress inside the step.
// Steps without children are returned as they are.
const getStepEntry = (name: string): string => {
  switch (name) {
    case "ads_structure":
      if (store.hasAdStructure()) return "structure";
      return store.showStructureTutorial
        ? "structureTutorial"
        : "structureSelection";

    case "ads":
      if (store.hasStartedAds()) return "adsAssembly";
      return store.showAdsTutorial ? "adsAssemblyTutorial" : "adsAssembly";

    case "launchpad":
      // The launchpad of a published campaign opens on its summary
      if (preCheckStore.isPublished) return "launchpadSummary";
      return store.showLaunchpadTutorial
        ? "launchpadTutorial"
        : "launchpadReviewCampaign";
  }

  return name;
};

// Find the first step not completed to use as initial step
const getInitialStep = () => {
  const targetStep = targetInitialStep.value;
  const initialStep = getStepEntry(targetStep || getFirstIncompleteStep());

  // The target step is only applied once, so reloading the page doesn't
  // keep sending the user back to it
  if (targetStep) {
    targetInitialStep.value = undefined;
  }

  return initialStep;
};

const getFirstIncompleteStep = () => {
  // Find the first step not completed
  const firstIncompleteStep = store.state.find(
    (stepValidation) => !stepValidation.completed,
  );

  if (!firstIncompleteStep) {
    return "launchpad";
  }

  // Map validator step to form step
  return validatorStepToFormStepMap[firstIncompleteStep.step];
};

const { currentFlatStep, goNext, goBack } =
  useMultiStepForm<FunnelPaidSocialFormData>(steps, {
    initialData: {
      ...props.data,
      funnelFlowId: paidSocialFunnel.id,
      channelGroupId: paidSocialFunnel.channel_group_id,
      channelGroup,
      campaign,
    },
    filterStep: (step) => userHas(step),
    initialStep: getInitialStep(),
    getStepEntry: (step) => {
      const entry = step.name ? getStepEntry(step.name) : undefined;

      // Without a specific entry, fall back to the default behavior
      return entry !== step.name ? entry : undefined;
    },
  });

watch(currentFlatStep, (step) => {
  // Clear precheck if the user goes out of the launchpad, unless it holds the
  // data of a published campaign, which is only fetched when the form loads
  if (!isLaunchpadStep(step.name) && !preCheckStore.isPublished) {
    preCheckStore.clearPrecheck();
  }
});

// Helper function to get fully translated error message
const getTranslatedError = (error: FunnelFlowValidatorStateError) => {
  const metadata = { ...error.metadata };

  // Try to translate each metadata value dynamically
  Object.keys(metadata).forEach((key) => {
    const value = metadata[key];
    if (value) {
      // Try to find a translation for this value
      const translationKey = `funnel-flow.paid-social.validator-errors.metadata-values.${value}`;

      // Only translate if a translation exists
      if (te(translationKey)) {
        metadata[key] = t(translationKey);
      }
    }
  });

  // Return the fully translated error message with translated metadata
  return t(`funnel-flow.paid-social.validator-errors.${error.code}`, metadata);
};

(window as any).goNext = goNext;
(window as any).goBack = goBack;
</script>

<template>
  <MultiStepForm>
    <template #tooltip="{ step }">
      <div class="tw:text-sm">
        <p class="tw:mb-1">
          {{ $t("funnel-flow.paid-social.validator-errors.tooltip-message") }}
        </p>

        <ul class="tw:list-disc tw:pl-9">
          <li
            v-for="error in store.state.find(
              (_step) => _step.step === step.name,
            )?.errors"
            :key="error.code"
          >
            {{ getTranslatedError(error) }}
          </li>
        </ul>
      </div>
    </template>

    <template #sidebarHeader>
      <SidebarTitle variant="secondary" size="sm">
        {{ $t("funnel-flow.paid-social.sidebar-menu.header") }}
      </SidebarTitle>

      <SidebarTitle>
        {{ campaign.name }}
      </SidebarTitle>
    </template>

    <FormStep name="channel">
      <FunnelPaidSocialFormChannel />
    </FormStep>

    <FormStep name="structureTutorial">
      <FunnelPaidSocialFormStructureTutorial />
    </FormStep>

    <FormStep name="structureSelection">
      <FunnelPaidSocialFormStructureSelection />
    </FormStep>

    <FormStep name="structure">
      <FunnelPaidSocialFormStructure />
    </FormStep>

    <FormStep name="audiences">
      <FunnelPaidSocialFormAudience />
    </FormStep>

    <FormStep name="ads_experiment">
      <FunnelPaidSocialFormCreativeAngle />
    </FormStep>

    <FormStep name="adsAssemblyTutorial">
      <FunnelPaidSocialFormAdsAssemblyTutorial />
    </FormStep>

    <FormStep name="adsAssembly">
      <FunnelPaidSocialFormAdsAssembly />
    </FormStep>

    <FormStep name="summary">
      <FunnelPaidSocialFormSummary />
    </FormStep>

    <!-- Review step hidden for now -->
    <!-- <FormStep name="review">
      <FunnelPaidSocialFormReview />
    </FormStep>

    <FormStep name="attachments">
      <FunnelPaidSocialFormReviewAttachments />
    </FormStep> -->

    <FormStep name="launchpadTutorial">
      <AdsLaunchpadTutorial />
    </FormStep>

    <FormStep name="launchpadReviewCampaign">
      <AdsLaunchpadReviewCampaign />
    </FormStep>

    <FormStep name="launchpadMediaPlan">
      <AdsLaunchpadMediaPlan />
    </FormStep>

    <FormStep name="launchpadTechnicalConfig">
      <AdsLaunchpadTechnicalConfig />
    </FormStep>

    <FormStep name="launchpadPreCheck">
      <AdsLaunchpadPreCheck />
    </FormStep>

    <FormStep name="launchpadSummary">
      <AdsLaunchpadSummary />
    </FormStep>

    <template #sidebarFooter>
      <SidebarLink
        :to="
          shouldBackToCampaign
            ? { name: 'CampaignSettings' }
            : { name: 'FunnelFlowHome' }
        "
        variant="link"
        icon="tabler-arrow-left"
      >
        {{
          shouldBackToCampaign
            ? $t("campaigns.back-to-campaign-with-name", {
                name: campaign.name,
              })
            : $t("funnel-flow.paid-social.sidebar-menu.back-to-funnel-flow")
        }}
      </SidebarLink>
    </template>
  </MultiStepForm>
</template>
