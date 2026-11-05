import { CampaignData } from "@/services/projects/CampaignsApi";
import FunnelFlowValidatorApi, {
  FunnelFlowValidator,
  FunnelFlowValidatorAdChannel,
} from "@/services/funnel-flow/FunnelFlowValidatorApi";

export const useFunnelPaidSocialFormStore = defineStore(
  "FunnelPaidSocialFormStore",
  () => {
    const campaign = ref<CampaignData | undefined>(undefined);
    const currentValidation = ref<FunnelFlowValidator | undefined>(undefined);

    const state = computed(() => currentValidation.value?.state ?? []);

    // "Don't show this message again" preferences of the video tutorials
    const showStructureTutorial = useLocalStorage(
      "paid-social-show-structure-tutorial",
      true,
    );
    const showAdsTutorial = useLocalStorage(
      "paid-social-show-ads-tutorial",
      true,
    );
    const showLaunchpadTutorial = useLocalStorage(
      "paid-social-show-launchpad-tutorial",
      true,
    );

    async function revalidate() {
      if (!campaign.value) {
        currentValidation.value = undefined;
        return;
      }

      // Run the validator
      const { data: response } =
        await FunnelFlowValidatorApi.getValidatorResults(campaign.value.id);

      // Save the response
      currentValidation.value = response;
    }

    async function initialize(_campaign: CampaignData) {
      campaign.value = _campaign;
      await revalidate();
    }

    function getStepValidation(stepName: string) {
      const step = currentValidation.value?.state.find(
        (step) => step.step === stepName,
      );

      return step;
    }

    function isStepDisabled(stepName: string) {
      if (!currentValidation.value?.state) {
        return true;
      }

      const index = currentValidation.value?.state.findIndex(
        (step) => step.step === stepName,
      );

      // If the step is not found in the array, disabled it
      if (index === undefined || index === -1) {
        return true;
      }

      // The first step is enabled
      if (index === 0) {
        return false;
      }

      // The step is enabled if it's completed
      if (currentValidation.value.state[index].completed) {
        return false;
      }

      // Get the index of the previous step
      const previousStepIndex = index - 1;

      // The step is disabled if the previous step is not completed
      if (!currentValidation.value.state[previousStepIndex].completed) {
        return true;
      }

      let incompletedCount = 0;
      for (let index = previousStepIndex; index >= 0; index--) {
        const _step = currentValidation.value.state[index];
        if (!_step.completed) {
          incompletedCount++;
        }
      }

      return incompletedCount > 0;
    }

    function doesStepHaveAlert(stepName: string) {
      if (!currentValidation.value) return false;

      const targetStep = currentValidation.value.state.find(
        (step) => step.step === stepName,
      );

      if (!targetStep) return false;

      return !targetStep.completed;
    }

    // Returns true if all steps before the given step (in validator order) are completed.
    function areAllPreviousStepsCompleted(stepName: string): boolean {
      const state = currentValidation.value?.state;
      if (!state) return false;

      const stepIndex = state.findIndex((s) => s.step === stepName);
      if (stepIndex === -1) return false;

      // All steps before the target must be completed
      for (let i = 0; i < stepIndex; i++) {
        if (!state[i].completed) return false;
      }
      return true;
    }

    // Get validator data for a specific ad set
    function getAdSetValidatorData(adSetId: number) {
      const validatorData = currentValidation.value?.funnel_flow_data;
      if (!validatorData) return undefined;

      return validatorData.find((adSet) => adSet.id === adSetId);
    }

    // Get validator data for a specific ad
    function getAdValidatorData(adSetId: number, adId: number) {
      const adSetData = getAdSetValidatorData(adSetId);
      if (!adSetData) return undefined;

      return adSetData.ads.find((ad) => ad.id === adId);
    }

    // Check if an ad set has dependencies (audiences, experiments, or filled ads)
    function adSetHasDependencies(adSetId: number): boolean {
      const adSetData = getAdSetValidatorData(adSetId);
      if (!adSetData) return false;

      const hasAudiences = adSetData.audiences.length > 0;
      const hasExperiments = adSetData.experiments.length > 0;
      const hasFilledAds = adSetHasFilledAds(adSetId);

      return hasAudiences || hasExperiments || hasFilledAds;
    }

    // Check if an ad channel has actual content (media, url, or payloads)
    function isAdChannelFilled(channel: FunnelFlowValidatorAdChannel): boolean {
      // Check if the media has a template id
      const hasMediaContent = !!channel.media.template_id?.trim?.();

      // Check if the channel has a url
      const hasUrl = !!channel.url?.trim?.();

      // Check if the channel has payloads
      const hasPayload =
        channel.channel_attributes?.some((attr) =>
          attr.payloads?.some((p) => p && Boolean(p.payload.trim())),
        ) ?? false;

      return hasMediaContent || hasUrl || hasPayload;
    }

    // Check if an ad set has any filled ads (ads with generated content)
    function adSetHasFilledAds(adSetId: number): boolean {
      const adSetData = getAdSetValidatorData(adSetId);
      if (!adSetData) return false;

      return adSetData.ads.some((ad) =>
        ad.attributes.ad_channels.some((channel) => isAdChannelFilled(channel)),
      );
    }

    // Check if a specific ad is filled (has content)
    function isAdFilled(adSetId: number, adId: number): boolean {
      const adData = getAdValidatorData(adSetId, adId);
      if (!adData) return false;

      return adData.attributes.ad_channels.some((channel) =>
        isAdChannelFilled(channel),
      );
    }

    // Check if the ad structure has been created (it has at least one ad set)
    function hasAdStructure(): boolean {
      return (currentValidation.value?.funnel_flow_data.length ?? 0) > 0;
    }

    // Check if the user started working on the ads: an ad set has a template
    // project linked, or an ad has content
    function hasStartedAds(): boolean {
      return (
        currentValidation.value?.funnel_flow_data.some(
          (adSet) =>
            !!adSet.media_platform_project_id || adSetHasFilledAds(adSet.id),
        ) ?? false
      );
    }

    // Count filled ads for an ad set
    function countFilledAds(adSetId: number): number {
      const adSetData = getAdSetValidatorData(adSetId);
      if (!adSetData) return 0;

      return adSetData.ads.filter((ad) =>
        ad.attributes.ad_channels.some((channel) => isAdChannelFilled(channel)),
      ).length;
    }

    return {
      campaign,
      state,
      currentValidation,

      initialize,
      revalidate,
      getStepValidation,

      isStepDisabled,
      doesStepHaveAlert,
      areAllPreviousStepsCompleted,

      // Validation helpers
      getAdSetValidatorData,
      getAdValidatorData,
      adSetHasDependencies,
      adSetHasFilledAds,
      isAdFilled,
      countFilledAds,
      hasAdStructure,
      hasStartedAds,

      // Tutorial preferences
      showStructureTutorial,
      showAdsTutorial,
      showLaunchpadTutorial,
    };
  },
);
