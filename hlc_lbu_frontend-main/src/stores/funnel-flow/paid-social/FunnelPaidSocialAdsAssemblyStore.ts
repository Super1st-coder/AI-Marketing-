import {
  FunnelFlowSidebarMenuItem,
  FunnelFlowSidebarSubMenuItem,
} from "@/components/funnel-flow/flows/paid-social/FunnelPaidSocialFormNewSideBar.vue";
import AbyssaleIntegrationApi, {
  AbyssaleProject,
} from "@/services/funnel-flow/paid-social/AbyssaleIntegrationApi";
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdByCampaignDefinitionData,
  getVariantVideo,
  isAdCompleted,
} from "@/services/funnel-flow/paid-social/AdsApi";
import AdsExperiment, {
  AdsExperimentByAdSetData,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdStructureApi, {
  AdSetData,
} from "@/services/funnel-flow/paid-social/AdStructureApi";
import AudienceApi, {
  AudiencesByChannel,
} from "@/services/projects/AudienceApi";
import CampaignsApi, { CampaignData } from "@/services/projects/CampaignsApi";
import VideoApi, {
  VideoProductionMode,
  VideoDraft,
  VideoSettings,
} from "@/services/funnel-flow/paid-social/VideoApi";

export type AdStructureWithAudienceAndCreativeAngle = AdSetData & {
  audiences: AudiencesByChannel[];
  experiment: AdsExperimentByAdSetData;
};

/** The flow an ad set follows. */
export type AdSetFormat = "image" | "video";

/** An ad with the progress saved for it in the video flow. */
export type AdWithVideoDraft = AdByCampaignDefinitionData & {
  draft: VideoDraft;
};

export type AdsAssemblyScreenName =
  | "home"
  | "assetOrigin"
  | "settings"
  | "refine"
  | "videoSettings"
  | "videoScripts"
  | "videoStoryboard"
  | "videoVoiceover"
  | "videoAd";

export type AdsAssemblyVideoScreenName = Extract<
  AdsAssemblyScreenName,
  `video${string}`
>;

/** The optional steps picked in the "Is the content ready?" modal. */
export type VideoContentOptions = Pick<
  VideoSettings,
  "storyboard_enabled" | "voiceover_enabled"
>;

/** The `current_step` the backend saves for each generation, and its screen. */
const VIDEO_STEP_SCREENS: Record<string, AdsAssemblyVideoScreenName> = {
  scripts: "videoScripts",
  storyboard: "videoStoryboard",
  // Saved when a single frame is generated again, in the same step
  "edit-shot": "videoStoryboard",
  voiceover: "videoVoiceover",
  // The Ad step. The Figma calls it "Video" in some places and "Ad" in others
  video: "videoAd",
  // The backend saves these when the clips are generated and assembled, which
  // the Ad step shows
  segments: "videoAd",
  assemble: "videoAd",
  // Saved when a single clip or audio is generated again, from the Ad step's
  // editor
  "segment-edit-shot": "videoAd",
  "regenerate-voice": "videoAd",
};

/**
 * The ordered screens of the video flow.
 *
 * Full Video always goes through the storyboard. Scripts Only adds the
 * storyboard and voiceover steps only when they were enabled in the
 * "Is the content ready?" modal; until then (`null`) it shows the base steps.
 */
export function getVideoScreens(
  productionMode: VideoProductionMode,
  options?: Partial<VideoContentOptions>,
): AdsAssemblyVideoScreenName[] {
  if (productionMode === "FULL_VIDEO") {
    return ["videoSettings", "videoScripts", "videoStoryboard", "videoAd"];
  }

  return [
    "videoSettings",
    "videoScripts",
    ...(options?.storyboard_enabled ? (["videoStoryboard"] as const) : []),
    ...(options?.voiceover_enabled ? (["videoVoiceover"] as const) : []),
    "videoAd",
  ];
}

export const useFunnelPaidSocialAdsAssemblyStore = defineStore(
  "FunnelPaidSocialAdsAssemblyStore",
  () => {
    const brandId = ref(-1);
    const campaignId = ref(-1);
    const channelGroupId = ref(-1);

    const campaign = ref<CampaignData>({} as CampaignData);

    const adGroups = ref<AdStructureWithAudienceAndCreativeAngle[]>([]);
    const ads = ref<Record<number, AdWithVideoDraft>>({});
    const assetOrigins = ref<AbyssaleProject[]>([]);

    const currentScreen = ref<AdsAssemblyScreenName>();

    // Ad sets for which the UGC/Video format was picked in this session. Only
    // needed until the scripts are generated: from then on the ad's saved
    // draft tells the format (see `getAdSetFormat`)
    const videoFormatAdSetIds = ref<Record<number, true>>({});

    // The ad set for which the ad format modal should be open, if any
    const formatModalAdSetId = ref<number | undefined>(undefined);

    const currentAd = ref<AdWithVideoDraft | undefined>(undefined);

    // Full Video until the scripts are generated, since it's the Settings
    // form's default mode
    const currentVideoScreens = computed(() =>
      getVideoScreens(
        currentAd.value?.draft.settings.production_mode ?? "FULL_VIDEO",
        currentAd.value?.draft.settings,
      ),
    );

    // Moves to the screen after (or before) `from` in the current ad's video
    // flow, so the optional steps are skipped when they're disabled
    function setAdjacentVideoScreen(
      from: AdsAssemblyVideoScreenName,
      offset: 1 | -1,
    ) {
      const screens = currentVideoScreens.value;
      const screen = screens[screens.indexOf(from) + offset];

      if (screen) {
        setScreen(screen);
      }
    }

    function setNextVideoScreen(from: AdsAssemblyVideoScreenName) {
      setAdjacentVideoScreen(from, 1);
    }

    function setPreviousVideoScreen(from: AdsAssemblyVideoScreenName) {
      setAdjacentVideoScreen(from, -1);
    }

    const currentSet = computed<
      AdStructureWithAudienceAndCreativeAngle | undefined
    >(() =>
      adGroups.value.find((adSet) =>
        adSet.ads.find((set) => set.id === currentAd.value?.ad_id),
      ),
    );

    // Which ad of the ad set the current ad is, 1-based
    const currentAdIndex = computed(
      () =>
        (currentSet.value?.ads.findIndex(
          (ad) => ad.id === currentAd.value?.ad_id,
        ) ?? -1) + 1,
    );

    const currentChannelId = ref<number | undefined>(undefined);
    const currentChannel = computed(() =>
      currentAd.value?.ad_channels.find(
        (channel) => channel.channel_id === currentChannelId.value,
      ),
    );

    const currentVariantId = ref<number | undefined>();
    const currentVariant = computed(() =>
      currentChannel.value?.variants.find(
        (variant) => variant.id === currentVariantId.value,
      ),
    );

    // What the draft keeps of the current variant (script, clips, video...),
    // found through the draft's `variant_rows`. Video ads only
    const currentVideoDraftVariant = computed(() => {
      const draft = currentAd.value?.draft;
      const rowId = currentVariantId.value;
      if (!draft || rowId === undefined) return undefined;

      const draftVariantId = Object.keys(draft.variant_rows).find(
        (key) => draft.variant_rows[key] === rowId,
      );

      return draftVariantId ? draft.variants[draftVariantId] : undefined;
    });

    const nextAd = computed(() => {
      for (const adSet of adGroups.value) {
        for (const ad of adSet.ads) {
          const adData = ads.value[ad.id];
          if (
            adData &&
            !_isAdCompleted(adData) &&
            ad.id !== currentAd.value?.ad_id
          ) {
            return {
              id: adData.ad_id,
              name: adData.ad_name,
            };
          }
        }
      }

      return undefined;
    });

    const nextAdSet = computed(() =>
      adGroups.value.find((adSet) =>
        adSet.ads.some((ad) => ad.id === nextAd.value?.id),
      ),
    );

    const currentAssetOrigin = computed(() =>
      currentSet.value
        ? assetOrigins.value.find(
            (project) =>
              currentSet.value?.media_platform_project_id !== undefined &&
              currentSet.value?.media_platform_project_id !== null &&
              project.id === currentSet.value.media_platform_project_id,
          )
        : undefined,
    );

    function isAdSetCompleted(adSet: AdStructureWithAudienceAndCreativeAngle) {
      return adSet.ads.every((ad) => _isAdCompleted(ads.value[ad.id]));
    }

    function _isAdCompleted(ad: AdWithVideoDraft) {
      return isAdCompleted(ad, ad.draft);
    }

    // The menu displated at the nested sidebar on the right
    const menu = computed<FunnelFlowSidebarMenuItem[]>(() => [
      // The "home" is actually a button. When clicked, the user is taken to the initial
      // screen with the list of ad groups
      {
        id: "home",
        label: campaign.value.name,
        selected: currentSet.value === undefined,
        click: () => moveToAdSet(undefined),
      },
      // Add the ad set buttons
      ...adGroups.value.map<FunnelFlowSidebarMenuItem>((adSet) => {
        const isVideo = getAdSetFormat(adSet) === "video";

        return {
          id: adSet.id,
          label: adSet.name,
          icon: "tabler:polaroid",
          hasSuccess: isAdSetCompleted(adSet),
          // Image: displayed as selected only if the current screen is "refine".
          // Video: the selected ad is the one highlighted, not the ad set
          selected:
            !isVideo &&
            currentSet.value?.id === adSet.id &&
            currentScreen.value !== "refine",
          // Display the menu subitems when it's the current selected ad set
          open: currentSet.value?.id === adSet.id,
          click: () => openAdSet(adSet.id),
          // Add the ad buttons nested inside the ad set menu item
          children: adSet.ads.map<FunnelFlowSidebarSubMenuItem>((ad) => {
            const adData = ads.value[ad.id];

            const item = {
              id: adData.ad_id,
              label: adData.ad_name,
              icon: "proicons-window",
              hasSuccess: _isAdCompleted(adData),
            };

            if (isVideo) {
              return {
                ...item,
                // Any ad can be opened. Each one has its own flow
                disabled: false,
                selected: currentAd.value?.ad_id === ad.id,
                click: async () => {
                  if (currentAd.value?.ad_id === ad.id) return;

                  await moveToAd(ad.id);
                  currentScreen.value = getVideoResumeScreen();
                },
              };
            }

            return {
              ...item,
              // Display it as enabled if the user is in the refine screen. Otherwise, display it
              // as disabled if the ad cannot be accessed (when the generation has not been run)
              disabled:
                currentScreen.value === "refine"
                  ? false
                  : !doesAdSetHaveGeneratedVariants(adSet) ||
                    !currentSet.value?.media_platform_project_id,
              selected:
                currentScreen.value === "refine" &&
                currentAd.value?.ad_id === ad.id,
              click: async () => {
                await moveToAd(ad.id);
                currentScreen.value = "refine";
              },
            };
          }),
        };
      }),
    ]);

    async function refetchAdSets() {
      if (!brandId.value || !campaign.value || !channelGroupId.value) {
        return;
      }

      // Fetch ad structure
      const { data: adStructure } =
        await AdStructureApi.getAdStructureByChannelGroup(
          brandId.value,
          campaign.value.id,
          channelGroupId.value,
        );

      // Fetch the audiences of all sets
      const [audiences, experiments] = await Promise.all([
        Promise.all(
          adStructure.ad_sets.map(
            async (set) =>
              (
                await AudienceApi.GetAudiencesByAdSet(
                  brandId.value,
                  campaign.value.id,
                  set.id,
                )
              ).data.audiences,
          ),
        ),
        Promise.all(
          adStructure.ad_sets.map(
            async (set) =>
              (
                await AdsExperiment.getExperimentByAdSet(
                  brandId.value,
                  campaign.value.id,
                  set.id,
                )
              ).data,
          ),
        ),
      ]);

      adGroups.value = adStructure.ad_sets.map((set, index) => ({
        ...set,
        audiences: audiences[index],
        experiment: experiments[index],
        ads: set.ads,
      }));
    }

    function _setCurrentAd(ad: AdWithVideoDraft) {
      const isTheSame = currentAd.value?.ad_id === ad.ad_id;

      currentAd.value = ad;

      currentChannelId.value = ad.ad_channels.find(
        (channel) => channel.channel_name === META_ADS_CHANNEL_NAME,
      )?.channel_id;

      if (!isTheSame) {
        currentVariantId.value = undefined;
      }
    }

    // Drafts saved before the backend paired each variant with its ad-channel
    // row have variants but no rows, so nothing can be saved per variant.
    // Saving the draft with the channel creates them. Once per draft, since
    // they're kept after that
    async function addVideoVariantRows(
      ad: AdByCampaignDefinitionData,
      draft: VideoDraft,
    ): Promise<VideoDraft> {
      const hasVariants = Object.keys(draft.variants).length > 0;
      const hasRows = Object.keys(draft.variant_rows ?? {}).length > 0;
      if (!hasVariants || hasRows) return draft;

      try {
        return await VideoApi.saveDraft({
          ad_id: ad.ad_id,
          channel_id: currentChannelId.value ?? ad.ad_channels[0]?.channel_id,
        });
      } catch (error) {
        // Without rows the flow still works, it just can't keep per-variant
        // flags, so loading the ad doesn't fail for it
        console.error("Failed to create the video variant rows:", error);
        return draft;
      }
    }

    // What the backend answers for an ad with no saved progress. Used where the
    // video flow is off, since the draft endpoint isn't deployed there
    function getEmptyVideoDraft(adId: number): VideoDraft {
      return {
        ad_id: adId,
        exists: false,
        settings: {},
        variants: {},
        current_step: "",
        jobs: {},
        variant_ids: [],
        variant_rows: {},
      };
    }

    async function refetchSingleAd(adId: number) {
      // Fetch the ad content and the video draft
      const [{ data }, savedDraft] = await Promise.all([
        AdsApi.getOneAd(brandId.value, campaignId.value, adId),
        IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT
          ? VideoApi.getDraft(adId)
          : getEmptyVideoDraft(adId),
      ]);

      const ad = {
        ...data,
        draft: await addVideoVariantRows(data, savedDraft),
      };
      ads.value = {
        ...ads.value,
        [adId]: ad,
      };

      if (currentAd.value?.ad_id === adId) {
        _setCurrentAd(ad);
      }

      return ad;
    }

    async function refetchAds() {
      const adIds = adGroups.value
        .map((adSet) => adSet.ads.map((ad) => ad.id))
        .flat();
      await Promise.all(adIds.map(async (id) => await refetchSingleAd(id)));
    }

    async function refetchAssetOrigins() {
      const { data } = await AbyssaleIntegrationApi.getList(brandId.value);
      assetOrigins.value = data;
    }

    async function initialize(
      _brandId: number,
      projectId: number,
      _campaignId: number,
      _channelGroupId: number,
    ) {
      currentAd.value = undefined;
      currentChannelId.value = undefined;

      brandId.value = _brandId;
      campaignId.value = _campaignId;
      channelGroupId.value = _channelGroupId;

      // Fetch campaign data
      campaign.value = (
        await CampaignsApi.getOne(_brandId, projectId, _campaignId)
      ).data;

      // Set the initial screen to the home
      currentScreen.value = "home";

      // Fetch all the ad sets, ads and asset origins data
      await refetchAdSets();
      await refetchAds();
      await refetchAssetOrigins();

      // Determine if some ad in any ad set has been touched
      const hasSomeAdWithTemplate = adGroups.value.some(
        (adSet) => getAdSetFormat(adSet) !== undefined,
      );

      const nextSet = nextAdSet.value;
      // An ad set that hasn't picked a format needs the format modal, which only
      // `openAdSet` shows. So when the video generation flow is enabled, we can only
      // auto-redirect to the next ad set if it has already picked a format.
      const canAutoRedirectToNextAdSet =
        nextSet !== undefined &&
        (!IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT ||
          getAdSetFormat(nextSet) !== undefined);

      if (hasSomeAdWithTemplate && canAutoRedirectToNextAdSet) {
        await moveToAdSet(nextSet.id);
      }
    }

    function setScreen(screen: AdsAssemblyScreenName) {
      currentScreen.value = screen;

      if (screen === "home") {
        currentAd.value = undefined;
      }
    }

    async function refetchCurrentAd() {
      if (currentAd.value !== undefined) {
        await refetchSingleAd(currentAd.value.ad_id);
      }
    }

    const moveToAd = async (adId: number | undefined) => {
      if (adId === undefined) {
        // Go home
        currentAd.value = undefined;
        return;
      }

      // Fetch the ad
      const ad = await refetchSingleAd(adId);

      // Update refs
      _setCurrentAd(ad);
    };

    // The format of the ad set, or undefined if it hasn't picked one yet.
    // Image if a media platform project was linked to it. Video if some of its
    // ads has a saved video draft, or if the format was picked in this session
    // (nothing is saved until the scripts are generated)
    function getAdSetFormat(adSet: AdSetData): AdSetFormat | undefined {
      if (adSet.media_platform_project_id) return "image";

      const hasVideoDraft =
        IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT &&
        adSet.ads.some((ad) => ads.value[ad.id]?.draft.exists);

      return hasVideoDraft || videoFormatAdSetIds.value[adSet.id]
        ? "video"
        : undefined;
    }

    const isCurrentSetVideoFormat = computed(() =>
      currentSet.value ? getAdSetFormat(currentSet.value) === "video" : false,
    );

    function openFormatModalForAdSet(adSetId: number) {
      formatModalAdSetId.value = adSetId;
    }

    function closeFormatModal() {
      formatModalAdSetId.value = undefined;
    }

    // Function to navigate to an ad set: opens the format modal if the ad set
    // hasn't picked a format yet, otherwise goes straight into its flow
    async function openAdSet(adSetId: number) {
      const adSet = adGroups.value.find((set) => set.id === adSetId);

      if (
        adSet &&
        IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT &&
        getAdSetFormat(adSet) === undefined
      ) {
        openFormatModalForAdSet(adSetId);
      } else {
        await moveToAdSet(adSetId);
      }
    }

    async function selectVideoFormatForAdSet(adSetId: number) {
      videoFormatAdSetIds.value = {
        ...videoFormatAdSetIds.value,
        [adSetId]: true,
      };

      await moveToAdSet(adSetId);
    }

    function doesAdSetHaveGeneratedVariants(adSet: AdSetData) {
      const adsFromCurrentSet = Object.values(ads.value).filter((ad) =>
        adSet.ads.some((_ad) => _ad.id === ad.ad_id),
      );

      const hasGeneratedVariants = adsFromCurrentSet.some((ad) => {
        const metaAdsChannel = ad.ad_channels.find(
          (channel) => channel.channel_name === META_ADS_CHANNEL_NAME,
        );

        return metaAdsChannel && metaAdsChannel.variants.length > 0;
      });

      return hasGeneratedVariants;
    }

    const doesCurrentAdSetHaveGeneratedVariants = computed(() =>
      currentSet.value
        ? doesAdSetHaveGeneratedVariants(currentSet.value)
        : false,
    );

    // The furthest step the current ad's video flow reached, which is where it
    // opens. Without scripts it's the first step, so a user with scripts is
    // never sent back to Settings, where continuing would generate (and charge)
    // them again. Otherwise it's the last step the backend saved, as long as
    // the flow has that step
    function getVideoResumeScreen(): AdsAssemblyVideoScreenName {
      const draft = currentAd.value?.draft;
      if (!draft || !Object.keys(draft.variants).length) return "videoSettings";

      const screen = VIDEO_STEP_SCREENS[draft.current_step];

      return screen && currentVideoScreens.value.includes(screen)
        ? screen
        : "videoScripts";
    }

    // The ad-channel row of one of the current ad's variants, from its draft
    // key ("v1" -> 1606). The id the variant endpoints take. Undefined for
    // drafts saved before the rows existed
    function getVideoVariantRowId(variantId: string): number | undefined {
      return currentAd.value?.draft.variant_rows[variantId];
    }

    // The finished video of one of the current ad's variants, by the
    // variant's id. Undefined for image ads, or while it has none
    function getCurrentAdVariantVideo(variantId: number | undefined) {
      return isCurrentSetVideoFormat.value &&
        currentAd.value &&
        variantId !== undefined
        ? getVariantVideo(variantId, currentAd.value.draft)
        : undefined;
    }

    async function moveToAdSet(
      id: number | undefined,
      adId?: number | undefined,
    ) {
      if (currentSet.value?.id === id && adId === undefined) {
        return;
      }

      // If the id is undefined, take the user to the homepage/index
      if (id === undefined) {
        // Go home
        await moveToAd(undefined);
        currentScreen.value = "home";
        return;
      }

      // Get ad set
      const adSet = adGroups.value.find((set) => set.id === id);
      if (!adSet) {
        throw new UnidentifiedError();
      }

      // Determine what ad to show when entering the ad set. The priority is:
      // 1. The ad specified by the adId parameter (if any)
      // 2. The ad of the ad set that is not completed (if any)
      // 3. The first ad of the set
      if (adId !== undefined) {
        await moveToAd(adId);
      } else if (nextAd.value && nextAdSet.value?.id === adSet.id) {
        await moveToAd(nextAd.value.id);
      } else {
        await moveToAd(adSet.ads[0].id);
      }

      // The ad set must had been set by this point, if not, something went wrong
      if (!currentSet.value) {
        throw new UnidentifiedError();
      }

      // Determine the initial screen
      if (isCurrentSetVideoFormat.value) {
        // Video generation

        currentScreen.value = getVideoResumeScreen();
      } else {
        // Image generation

        if (currentSet.value.media_platform_project_id) {
          // The ad set has a media platform project linked to i
          currentScreen.value = doesCurrentAdSetHaveGeneratedVariants.value
            ? "refine"
            : "settings";
        } else {
          // The ad set doesn't have a project linked to it, so the user must pick one first
          currentScreen.value = "assetOrigin";
        }
      }
    }

    function setCurrentVariantId(adVariantId: number) {
      currentVariantId.value = adVariantId;
    }

    return {
      brandId,
      campaignId,
      channelGroupId,
      campaign,
      refetchAdSets,
      initialize,
      adGroups,
      ads,
      projects: assetOrigins,
      currentAssetOrigin,
      refetchAssetOrigins,
      menu,
      isAdCompleted: _isAdCompleted,
      isAdSetCompleted,
      nextAd,
      nextAdSet,
      moveToAdSet,
      openAdSet,
      refetchCurrentAd,
      refetchSingleAd,
      moveToAd,
      currentScreen,
      setScreen,
      currentSet,
      currentAd,
      currentVariant,
      currentChannel,
      setCurrentVariantId,
      doesCurrentAdSetHaveGeneratedVariants,
      isCurrentSetVideoFormat,
      formatModalAdSetId,
      openFormatModalForAdSet,
      closeFormatModal,
      selectVideoFormatForAdSet,
      currentAdIndex,
      currentVideoScreens,
      setNextVideoScreen,
      setPreviousVideoScreen,
      getVideoResumeScreen,
      getVideoVariantRowId,
      getCurrentAdVariantVideo,
      currentVideoDraftVariant,
    };
  },
);
