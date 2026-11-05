import AudienceApi, {
  AudiencesByChannel,
} from "@/services/projects/AudienceApi";
import AdsExperiment, {
  AdsExperimentByAdSetData,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdsApi, { AdVariant } from "@/services/funnel-flow/paid-social/AdsApi";
import CampaignsApi, { CampaignData } from "@/services/projects/CampaignsApi";
import ChannelConnections, {
  LaunchPreCheckRequest,
  LaunchPreCheckResponse,
  LaunchPreCheckCreative,
  LaunchPreCheckLocation,
  type PreCheckTextsRequest,
  type PreCheckImagesRequest,
  type PreCheckBudgetRequest,
  type PreCheckCTAsRequest,
  type PreCheckProposalUrlRequest,
  type PreCheckLocationsRequest,
} from "@/services/funnel-flow/ChannelConnections";

export type CreativeWithData = LaunchPreCheckCreative & {
  audiences: AudiencesByChannel[];
  experiment: AdsExperimentByAdSetData;
  // Selected ad variant, used by the campaign-upload success modal to report
  // the real leftover assets not included in the pinned combination.
  adVariant: AdVariant;
  // Name of the ad. The creative `name` is the name of its ad set
  adName: string;
};

export const useFunnelPaidSocialLaunchpadPreCheckStore = defineStore(
  "FunnelPaidSocialLaunchpadPreCheckStore",
  () => {
    const brandId = ref<number>(-1);
    const campaignId = ref<number>(-1);
    const projectId = ref<number>(-1);

    const campaign = ref<CampaignData | undefined>(undefined);
    const preCheckResponse = ref<LaunchPreCheckResponse | undefined>(undefined);

    // Configuration of the current launch, used to restore the technical
    // configuration form. A published campaign only knows the part of it
    // returned by the publish endpoint
    const launchConfiguration = ref<Partial<LaunchPreCheckRequest> | undefined>(
      undefined,
    );

    // Meta Ads link of the published campaign, returned by the publish task
    const metaUrl = ref<string | undefined>(undefined);

    // Whether the campaign has already been published to the channel
    const isPublished = ref(false);

    const campaignUploadSuccessModalOpen = ref(false);

    // Immutable copy for modals
    const initialCreativesWithData = ref<CreativeWithData[]>([]);

    // Current state mutated by re-runs
    const creativesWithData = ref<CreativeWithData[]>([]);

    // Per-creative selected indices
    const selectedIndices = ref<
      Record<
        number,
        {
          bodies: number[];
          titles: number[];
          descriptions: number[];
          images: number[];
        }
      >
    >({});

    // Per-creative minimum budgets
    const minimumBudgets = ref<Record<number, number>>({});

    // Per-creative selected CTAs (values, not indices)
    const selectedCTAs = ref<Record<number, string[]>>({});

    // Per-creative proposal URLs
    const proposalUrls = ref<Record<number, string>>({});

    // Per-creative locations
    const locations = ref<Record<number, LaunchPreCheckLocation[]>>({});

    async function initialize(
      _projectId: number,
      request: LaunchPreCheckRequest,
    ) {
      brandId.value = request.brand_id;
      campaignId.value = request.campaign_id;
      projectId.value = _projectId;

      // Fetch campaign
      await fetchCampaign();

      // A new pre-check replaces the data of the published campaign
      isPublished.value = false;
      metaUrl.value = undefined;

      // Call pre-check API
      const response = await ChannelConnections.generateLaunchPreCheck(request);
      preCheckResponse.value = response;
      launchConfiguration.value = request;

      await loadCreatives(response.data.creatives);
    }

    /**
     * Loads the launchpad with the data of an already published campaign, so
     * the summary can be displayed without running the pre-check again.
     *
     * Returns `false` when the campaign has not been published yet.
     */
    async function initializeFromPublished(
      _projectId: number,
      _brandId: number,
      _campaignId: number,
    ) {
      const response = await ChannelConnections.getPublishedLaunch(
        _brandId,
        _campaignId,
      );

      // The campaign has not been published to the channel yet
      if (!response) {
        return false;
      }

      brandId.value = _brandId;
      campaignId.value = _campaignId;
      projectId.value = _projectId;

      // Fetch campaign
      await fetchCampaign();

      preCheckResponse.value = response;
      launchConfiguration.value = {
        brand_id: _brandId,
        campaign_id: _campaignId,
        objective: response.data.campaign.objective,
        optimization_goal: response.data.campaign.optimization_goal,
        creative_type: response.data.campaign.mode,
        conversion_event: response.data.campaign.conversion_event,
      };
      metaUrl.value = response.data.meta_url;
      isPublished.value = true;

      await loadCreatives(response.data.creatives);

      return true;
    }

    async function fetchCampaign() {
      const { data: campaignData } = await CampaignsApi.getOne(
        brandId.value,
        projectId.value,
        campaignId.value,
      );
      campaign.value = campaignData;
    }

    // Fetch audiences, experiments and ad variants of each creative and
    // initialize the state derived from them
    async function loadCreatives(creatives: LaunchPreCheckCreative[]) {
      // Fetch audiences and experiments for each creative
      const creativesWithAllData: CreativeWithData[] = await Promise.all(
        creatives.map(async (creative) => {
          const [audiencesResponse, experimentResponse, adResponse] =
            await Promise.all([
              AudienceApi.GetAudiencesByAdSet(
                brandId.value!,
                campaignId.value!,
                creative.adset_id,
              ),
              AdsExperiment.getExperimentByAdSet(
                brandId.value!,
                campaignId.value!,
                creative.adset_id,
              ),
              AdsApi.getOneAd(brandId.value, campaignId.value, creative.ad_id),
            ]);

          // `adchannel_id` identifies the specific ad variant used for this
          // creative
          const variant = adResponse.data.ad_channels
            .flatMap((adChannel) => adChannel.variants)
            .find((adVariant) => adVariant.id === creative.adchannel_id);
          assert(variant, "Ad variant not found for creative");

          // Return creative with audiences and experiment
          return {
            ...creative,
            audiences: audiencesResponse.data.audiences,
            experiment: experimentResponse.data,
            adVariant: variant,
            adName: adResponse.data.ad_name,
          };
        }),
      );

      // Set creatives with data and initial creatives with data
      creativesWithData.value = creativesWithAllData;
      initialCreativesWithData.value = structuredClone(creativesWithAllData);

      // Initialize selected indices
      selectedIndices.value = {};
      creativesWithAllData.forEach((creative) => {
        selectedIndices.value[creative.idx] = {
          bodies: creative.bodies.map((_, i) => i),
          titles: creative.titles.map((_, i) => i),
          descriptions: creative.descriptions.map((_, i) => i),
          images: creative.images.map((_, i) => i),
        };
      });

      // Initialize minimum budgets
      minimumBudgets.value = {};
      creativesWithAllData.forEach((creative) => {
        minimumBudgets.value[creative.idx] = creative.min_daily_budget;
      });

      // Initialize selected CTAs from valid CTAs only
      selectedCTAs.value = {};
      creativesWithAllData.forEach((creative) => {
        selectedCTAs.value[creative.idx] = creative.call_to_action_types.map(
          (cta) => cta.value,
        );
      });

      // Initialize proposal URLs
      proposalUrls.value = {};
      creativesWithAllData.forEach((creative) => {
        proposalUrls.value[creative.idx] = creative.proposal_url;
      });

      // Initialize locations
      locations.value = {};
      creativesWithAllData.forEach((creative) => {
        locations.value[creative.idx] = creative.locations;
      });
    }

    function getInitialCreative(
      creativeId: number,
    ): CreativeWithData | undefined {
      return initialCreativesWithData.value.find((c) => c.idx === creativeId);
    }

    function getSelectedBodies(creativeId: number): number[] {
      return selectedIndices.value[creativeId]?.bodies ?? [];
    }

    async function setSelectedBodies(creativeId: number, indices: number[]) {
      selectedIndices.value[creativeId].bodies = indices;
      await rerunPreCheckTextsForCreative(creativeId);
    }

    function getSelectedTitles(creativeId: number): number[] {
      return selectedIndices.value[creativeId]?.titles ?? [];
    }

    async function setSelectedTitles(creativeId: number, indices: number[]) {
      selectedIndices.value[creativeId].titles = indices;
      await rerunPreCheckTextsForCreative(creativeId);
    }

    function getSelectedDescriptions(creativeId: number): number[] {
      return selectedIndices.value[creativeId]?.descriptions ?? [];
    }

    async function setSelectedDescriptions(
      creativeId: number,
      indices: number[],
    ) {
      selectedIndices.value[creativeId].descriptions = indices;
      await rerunPreCheckTextsForCreative(creativeId);
    }

    function getSelectedImages(creativeId: number): number[] {
      return selectedIndices.value[creativeId]?.images ?? [];
    }

    async function setSelectedImages(creativeId: number, indices: number[]) {
      selectedIndices.value[creativeId].images = indices;
      await rerunPreCheckImagesForCreative(creativeId);
    }

    async function rerunPreCheckImagesForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      const selected = selectedIndices.value[creativeId];
      const images = selected.images.map((i) => initial.images[i]);

      const payload: PreCheckImagesRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        images,
      };

      const response =
        await ChannelConnections.saveAndValidatePreCheckImages(payload);

      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              images: response.data.images,
              images_valid_amount: response.data.images_valid_amount,
            }
          : creative,
      );
    }

    async function setSelectedTextIndices(
      creativeId: number,
      payload: {
        bodies: number[];
        titles: number[];
        descriptions: number[];
      },
    ) {
      selectedIndices.value[creativeId].bodies = payload.bodies;
      selectedIndices.value[creativeId].titles = payload.titles;
      selectedIndices.value[creativeId].descriptions = payload.descriptions;
      await rerunPreCheckTextsForCreative(creativeId);
    }

    async function rerunPreCheckTextsForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      // Get selected indices
      const selected = selectedIndices.value[creativeId];

      // Get selected texts
      const bodies = selected.bodies.map((i) => initial.bodies[i]);
      const titles = selected.titles.map((i) => initial.titles[i]);
      const descriptions = selected.descriptions.map(
        (i) => initial.descriptions[i],
      );

      // Create payload
      const payload: PreCheckTextsRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        bodies,
        titles,
        descriptions,
      };

      // Call pre-check API
      const response =
        await ChannelConnections.saveAndValidatePreCheckTexts(payload);

      // Get existing creative
      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      // Update creative
      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              bodies: response.data.bodies,
              titles: response.data.titles,
              descriptions: response.data.descriptions,
              titles_valid_amount: response.data.titles_valid_amount,
              bodies_valid_amount: response.data.bodies_valid_amount,
              descriptions_valid_amount:
                response.data.descriptions_valid_amount,
              unique_titles: response.data.unique_titles,
              unique_bodies: response.data.unique_bodies,
              unique_descriptions: response.data.unique_descriptions,
            }
          : creative,
      );
    }

    async function rerunPreCheckBudgetForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      // Get selected indices
      const daily_budget = minimumBudgets.value[creativeId];

      // Create payload
      const payload: PreCheckBudgetRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        daily_budget: daily_budget,
      };

      // Call pre-check API
      const response =
        await ChannelConnections.saveAndValidatePreCheckBudget(payload);

      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              daily_budget: response.data.daily_budget,
              daily_budget_valid: response.data.daily_budget_valid,
            }
          : creative,
      );
    }

    function getMinimumBudget(creativeId: number): number {
      return minimumBudgets.value[creativeId];
    }

    async function setMinimumBudget(creativeId: number, dailyBudget: number) {
      minimumBudgets.value[creativeId] = dailyBudget;
      await rerunPreCheckBudgetForCreative(creativeId);
    }

    function getSelectedCTAs(creativeId: number): string[] {
      return selectedCTAs.value[creativeId];
    }

    async function setSelectedCTAs(creativeId: number, ctaValues: string[]) {
      selectedCTAs.value[creativeId] = ctaValues;
      await rerunPreCheckCTAsForCreative(creativeId);
    }

    async function rerunPreCheckCTAsForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      const selected = selectedCTAs.value[creativeId] ?? [];
      const call_to_action_types = selected.map((value) => ({
        value,
        valid: true,
      }));

      const payload: PreCheckCTAsRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        call_to_action_types,
      };

      const response =
        await ChannelConnections.saveAndValidatePreCheckCTAs(payload);

      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              call_to_action_types: response.data.call_to_action_types,
              call_to_action_types_valid_amount:
                response.data.call_to_action_types_valid_amount,
            }
          : creative,
      );
    }

    function getProposalUrl(creativeId: number): string {
      return proposalUrls.value[creativeId];
    }

    async function setProposalUrl(creativeId: number, proposalUrl: string) {
      proposalUrls.value[creativeId] = proposalUrl;
      await rerunPreCheckProposalUrlForCreative(creativeId);
    }

    async function rerunPreCheckProposalUrlForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      const proposal_url = proposalUrls.value[creativeId];

      const payload: PreCheckProposalUrlRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        proposal_url,
      };

      const response =
        await ChannelConnections.saveAndValidatePreCheckProposalUrl(payload);

      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              proposal_url: response.data.proposal_url,
              proposal_url_valid: response.data.proposal_url_valid,
            }
          : creative,
      );
    }

    function getLocations(creativeId: number): LaunchPreCheckLocation[] {
      return locations.value[creativeId];
    }

    async function setLocations(
      creativeId: number,
      newLocations: LaunchPreCheckLocation[],
    ) {
      locations.value[creativeId] = newLocations;
      await rerunPreCheckLocationsForCreative(creativeId);
    }

    async function rerunPreCheckLocationsForCreative(creativeId: number) {
      const initial = getInitialCreative(creativeId);
      if (!initial) {
        throw new Error("Initial creative not found");
      }

      const currentLocations = locations.value[creativeId];

      const payload: PreCheckLocationsRequest = {
        brand_id: brandId.value,
        campaign_id: campaignId.value,
        adset_id: initial.adset_id,
        ad_id: initial.ad_id,
        adchannel_id: initial.adchannel_id,
        locations: currentLocations,
      };

      const response =
        await ChannelConnections.saveAndValidatePreCheckLocations(payload);

      const existing = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!existing) {
        throw new Error("Existing creative not found");
      }

      // Update locations ref with response data
      locations.value[creativeId] = response.data.locations;

      creativesWithData.value = creativesWithData.value.map((creative) =>
        creative.idx === creativeId
          ? {
              ...creative,
              locations: response.data.locations,
              locations_valid: response.data.locations_valid,
            }
          : creative,
      );
    }

    // Validation helper functions
    function getTextLengthError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      const hasInvalidLength =
        creative.bodies.some((body) => !body.valid_length) ||
        creative.titles.some((title) => !title.valid_length) ||
        creative.descriptions.some((desc) => !desc.valid_length);

      return hasInvalidLength ? "Limit Exceeded" : undefined;
    }

    function getDuplicateCheckError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      const hasDuplicates =
        !creative.unique_titles ||
        !creative.unique_bodies ||
        !creative.unique_descriptions;

      return hasDuplicates ? "Dupls Found" : undefined;
    }

    function getPrimaryTextCountError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.bodies_valid_amount) {
        return `Max ${creative.bodies_max_amount}`;
      }
      return undefined;
    }

    function getHeadlinesCountError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.titles_valid_amount) {
        return `Max ${creative.titles_max_amount}`;
      }
      return undefined;
    }

    function getDescriptionCountError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.descriptions_valid_amount) {
        return `Max ${creative.descriptions_max_amount}`;
      }
      return undefined;
    }

    function getCtaError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      const hasInvalidCta = creative.call_to_action_types.some(
        (cta) => !cta.valid,
      );
      const hasInvalidAmount = !creative.call_to_action_types_valid_amount;

      if (hasInvalidCta || hasInvalidAmount) {
        return "Invalid CTA";
      }
      return undefined;
    }

    function getBudgetError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.daily_budget_valid) {
        return `Below Min (${creative.min_daily_budget})`;
      }
      return undefined;
    }

    function getUrlError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.proposal_url_valid) {
        return "Invalid URL";
      }
      return undefined;
    }

    function getTargetingError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.locations_valid) {
        return "Missing Location";
      }
      return undefined;
    }

    function getMediaTypesError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      // Media types validation not yet available in precheck API
      return undefined;
    }

    function getMediaSpecsError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      const hasInvalidSpecs = creative.images.some((image) => !image.valid);
      if (hasInvalidSpecs) {
        return "Invalid Specs";
      }
      return undefined;
    }

    function getImageCountError(creativeId: number): string | undefined {
      const creative = creativesWithData.value.find(
        (c) => c.idx === creativeId,
      );
      if (!creative) return undefined;

      if (!creative.images_valid_amount) {
        return `Max ${creative.images_max_amount}`;
      }
      return undefined;
    }

    function getAllErrors(creativeId: number) {
      return {
        textLength: getTextLengthError(creativeId),
        duplicateCheck: getDuplicateCheckError(creativeId),
        primaryTextCount: getPrimaryTextCountError(creativeId),
        headlinesCount: getHeadlinesCountError(creativeId),
        descriptionCount: getDescriptionCountError(creativeId),
        cta: getCtaError(creativeId),
        budget: getBudgetError(creativeId),
        url: getUrlError(creativeId),
        targeting: getTargetingError(creativeId),
        mediaTypes: getMediaTypesError(creativeId),
        mediaSpecs: getMediaSpecsError(creativeId),
        imageCount: getImageCountError(creativeId),
      };
    }

    function getErrorCount(creativeId: number): number {
      const errors = getAllErrors(creativeId);
      return Object.values(errors).filter((error) => error !== undefined)
        .length;
    }

    const hasErrorsInAnyAd = computed(() =>
      creativesWithData.value.some(
        (creative) => getErrorCount(creative.idx) > 0,
      ),
    );

    // TODO: once back-end is completed, check that this is the correct way to determine the standard mode
    const isStandardMode = computed(
      () => preCheckResponse.value?.data.campaign.mode === "STANDARD",
    );

    function clearPrecheck() {
      preCheckResponse.value = undefined;
      launchConfiguration.value = undefined;
      metaUrl.value = undefined;
      isPublished.value = false;
      campaignUploadSuccessModalOpen.value = false;
      initialCreativesWithData.value = [];
      creativesWithData.value = [];
      selectedIndices.value = {};
      minimumBudgets.value = {};
      selectedCTAs.value = {};
      proposalUrls.value = {};
      locations.value = {};
    }

    function clear() {
      brandId.value = -1;
      campaignId.value = -1;
      projectId.value = -1;
      campaign.value = undefined;
      clearPrecheck();
    }

    return {
      brandId,
      campaignId,
      projectId,
      campaign,
      preCheckResponse,
      launchConfiguration,
      metaUrl,
      isPublished,
      campaignUploadSuccessModalOpen,
      initialCreativesWithData,
      creativesWithData,
      selectedIndices,
      minimumBudgets,
      initialize,
      initializeFromPublished,
      getInitialCreative,
      getSelectedBodies,
      setSelectedBodies,
      getSelectedTitles,
      setSelectedTitles,
      getSelectedDescriptions,
      setSelectedDescriptions,
      getSelectedImages,
      setSelectedImages,
      setSelectedTextIndices,
      rerunPreCheckTextsForCreative,
      rerunPreCheckBudgetForCreative,
      getMinimumBudget,
      setMinimumBudget,
      getSelectedCTAs,
      setSelectedCTAs,
      rerunPreCheckCTAsForCreative,
      getProposalUrl,
      setProposalUrl,
      rerunPreCheckProposalUrlForCreative,
      getLocations,
      setLocations,
      rerunPreCheckLocationsForCreative,
      getTextLengthError,
      getDuplicateCheckError,
      getPrimaryTextCountError,
      getHeadlinesCountError,
      getDescriptionCountError,
      getCtaError,
      getBudgetError,
      getUrlError,
      getTargetingError,
      getMediaTypesError,
      getMediaSpecsError,
      getImageCountError,
      getErrorCount,
      hasErrorsInAnyAd,
      isStandardMode,
      clear,
      clearPrecheck,
    };
  },
);
