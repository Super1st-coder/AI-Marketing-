import { AdSetSidebar } from "@/components/funnel-flow/flows/paid-social/FunnelPaidSocialFormSideBar.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import AudienceApi, {
  AudienceCreationBodyWithManualData,
  AudienceCreationBodyWithDescriptionOrFiles,
  AudiencesByChannel,
  CancelProposalAudiencesBody,
  CreateAudienceFromSavedBody,
  SetPreferredAudienceBody,
  UpdatePreferredAudienceBody,
} from "@/services/projects/AudienceApi";
import AudicenceApi from "@/services/projects/AudienceApi";

export type StepKey =
  | "IDLE"
  | "START"
  | "GENERATE_AUD_LOADER"
  | "SAVED_AUDIENCE"
  | "GENERATED_AUDIENCE"
  | "CREATE_MANUAL"
  | "END_MESSAGE"
  | "ADD_COMMENT"
  | "CANCEL_AUDIENCE"
  | "DELETE_AUDIENCE"
  | "EDIT_AUDIENCE";

export const useFunnelPaidSocialAudienceStore = defineStore(
  "FunnelPaidSocialAudienceStore",
  () => {
    const paidSocialFormStore = useFunnelPaidSocialFormStore();

    const brandId = ref<number | null>(null);
    const campaignId = ref<number | null>(null);

    const adSets = ref<AdSetSidebar[]>([]);
    const selectedAdSetIndex = ref<number>(0);
    const selectedAdSet = computed(
      () => adSets.value[selectedAdSetIndex.value],
    );
    const nextSet = computed(() =>
      adSets.value.find(
        (set) => set.hasAlert && set.id !== selectedAdSet.value.id,
      ),
    );

    const allAudiences = ref<AudiencesByChannel[][]>([]);
    const currentAudiences = computed<AudiencesByChannel[]>({
      get: () => allAudiences.value[selectedAdSetIndex.value],
      set: (newAudiences) => {
        allAudiences.value = allAudiences.value.map((audiences, index) =>
          index === selectedAdSetIndex.value ? newAudiences : audiences,
        );
      },
    });

    const savedAudiences = ref<AudiencesByChannel[]>([]);

    type UsageInfo = { adSetId: number; adSetIndex: number; adSetName: string };
    const normalize = (s: string) =>
      (s ?? "")
        .toString()
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");

    const usedSavedAudiencesById = computed(() => {
      const map: Record<number, Record<number, UsageInfo>> = {};
      allAudiences.value.forEach((audiencesForSet, setIndex) => {
        audiencesForSet?.forEach((channel) => {
          const preferred = channel.preferred_audience;
          if (!preferred) return;
          if (!map[channel.channel_id]) map[channel.channel_id] = {};
          const adSet = adSets.value[setIndex];
          map[channel.channel_id][preferred.id] = {
            adSetId: adSet?.id,
            adSetIndex: setIndex,
            adSetName: adSet?.name ?? `Ad Set ${setIndex + 1}`,
          };
        });
      });
      return map;
    });

    const usedSavedAudiencesByName = computed(() => {
      const map: Record<number, Record<string, UsageInfo>> = {};
      allAudiences.value.forEach((audiencesForSet, setIndex) => {
        audiencesForSet?.forEach((channel) => {
          const preferred = channel.preferred_audience;
          if (!preferred) return;
          if (!map[channel.channel_id]) map[channel.channel_id] = {};
          const adSet = adSets.value[setIndex];
          map[channel.channel_id][normalize(preferred.name)] = {
            adSetId: adSet?.id,
            adSetIndex: setIndex,
            adSetName: adSet?.name ?? `Ad Set ${setIndex + 1}`,
          };
        });
      });
      return map;
    });

    function getSavedAudienceUsage(
      channelId: number,
      audience: { id: number; name: string } | undefined | null,
    ): UsageInfo | null {
      if (!audience) return null;
      // TODO: This validation works only if the audience id is unique.
      /* const byId = usedSavedAudiencesById.value[channelId]?.[audience.id];
    if (byId) return byId; */
      const byName =
        usedSavedAudiencesByName.value[channelId]?.[normalize(audience.name)];
      return byName ?? null;
    }

    watch(
      allAudiences,
      (allAudiences) => {
        adSets.value = adSets.value.map((set, index) => {
          const targetAudiences = allAudiences[index];

          return {
            ...set,
            hasAlert:
              targetAudiences.length === 0 ||
              targetAudiences.some(
                (audience) => audience.preferred_audience === null,
              ),
          };
        });
      },
      { immediate: true },
    );

    const currentStep = ref<StepKey>("IDLE");

    const showAddSetModal = computed(() => currentStep.value === "START");
    const showGenerateAudLoader = computed(
      () => currentStep.value === "GENERATE_AUD_LOADER",
    );
    const showSavedAudience = computed(
      () => currentStep.value === "SAVED_AUDIENCE",
    );
    const showGeneratedAudience = computed(
      () => currentStep.value === "GENERATED_AUDIENCE",
    );
    const showCreateManual = computed(
      () => currentStep.value === "CREATE_MANUAL",
    );
    const showEndMsg = computed(() => currentStep.value === "END_MESSAGE");
    const showAddComment = computed(() => currentStep.value === "ADD_COMMENT");
    const showCancelAudience = computed(
      () => currentStep.value === "CANCEL_AUDIENCE",
    );
    const showDeleteAudience = computed(
      () => currentStep.value === "DELETE_AUDIENCE",
    );
    const showEditAudience = computed(
      () => currentStep.value === "EDIT_AUDIENCE",
    );

    function setStep(step: StepKey) {
      currentStep.value = step;
    }

    function openGenerateAudLoader() {
      setStep("GENERATE_AUD_LOADER");
    }
    function openSavedAudienceModal() {
      setStep("SAVED_AUDIENCE");
    }
    function startManual() {
      setStep(
        currentAudiences.value.length > 0
          ? "GENERATED_AUDIENCE"
          : "CREATE_MANUAL",
      );
    }

    function closeAllModals() {
      currentStep.value = "IDLE";
    }

    async function loadAdSets(channelGroupId) {
      if (brandId.value == null || campaignId.value == null) {
        throw new Error(
          "AudienceWizard: setContext({ brand, campaign }) primero.",
        );
      }

      // Get the ad structure
      const { data } = await AdStructureApi.getAdStructureByChannelGroup(
        brandId.value,
        campaignId.value,
        channelGroupId,
      );

      // Fetch the audiences of all sets
      allAudiences.value = await Promise.all(
        data.ad_sets.map(
          async (set) =>
            (
              await AudienceApi.GetAudiencesByAdSet(
                brandId.value!,
                campaignId.value!,
                set.id,
              )
            ).data.audiences,
        ),
      );

      // Save the structure
      adSets.value = data.ad_sets.map((set, index) => ({
        ...set,
        open: false,
        hasAlert: allAudiences.value[index].length === 0,
      }));

      // Select the first set
      if (adSets.value.length) {
        await selectAdSet(adSets.value[0].id);
      }
    }

    async function loadSavedAudiences() {
      if (brandId.value == null) {
        throw new Error("AudienceWizard: brandId no puede ser null");
      }
      const { data } = await AudicenceApi.GetSavedAudiences(brandId.value);
      savedAudiences.value = data.map((audience) => ({
        ...audience,
        saved_audiences: audience.saved_audiences
          ? audience.saved_audiences.map((savedAudience) => ({
              ...savedAudience,
              saved: true,
            }))
          : null,
      }));
    }

    async function selectAdSet(id: number) {
      if (brandId.value == null || campaignId.value == null) {
        throw new Error(
          "AudienceWizard: setContext({ brand, campaign }) primero.",
        );
      }

      const index = adSets.value.findIndex((set) => set.id === id);
      selectedAdSetIndex.value = index;
      closeAllModals();
    }

    async function generateAudiencesWithManualData(
      audience: AudienceCreationBodyWithManualData,
    ) {
      const { data } =
        await AudicenceApi.GenerateAudiencesWithManualData(audience);
      currentAudiences.value = data;
    }

    async function generateAudiencesFromDescriptionOrFile(
      audience: AudienceCreationBodyWithDescriptionOrFiles,
    ) {
      const { data } =
        await AudicenceApi.generateAudiencesFromDescriptionOrFile(audience);
      currentAudiences.value = data;
    }

    async function saveAudience(body: any) {
      const { data } = await AudicenceApi.SaveAudience(body);
      const idx = currentAudiences.value.findIndex(
        (p) => p.channel_id === data.channel_id,
      );
      currentAudiences.value[idx] = data;
    }

    async function unsaveAudience(body: any) {
      const { data } = await AudicenceApi.UnsaveAudience(body);
      const idx = currentAudiences.value.findIndex(
        (p) => p.channel_id === data.channel_id,
      );
      currentAudiences.value[idx] = data;
    }

    async function deleteAudienceFromSaved(audienceSavedId: number) {
      const { ok } =
        await AudicenceApi.DeleteAudienceFromSaved(audienceSavedId);
      if (ok) {
        await loadSavedAudiences();
      }
    }

    async function deleteAudience(body: any) {
      const { data } = await AudienceApi.DeleteAudience(body);

      currentAudiences.value = currentAudiences.value.map((audience) =>
        audience.channel_id === data.channel_id ? data : audience,
      );

      // Revalidate funnel flow
      await paidSocialFormStore.revalidate();
    }

    async function setPreferredAudience(body: SetPreferredAudienceBody) {
      const { data } = await AudicenceApi.SetPreferredAudience(body);

      currentAudiences.value = currentAudiences.value.map((audience) =>
        audience.channel_id === data.channel_id ? data : audience,
      );

      // Revalidate funnel flow
      await paidSocialFormStore.revalidate();
    }

    async function updatePreferredAudience(body: UpdatePreferredAudienceBody) {
      const { data } = await AudicenceApi.UpdatePreferredAudience(body);
      currentAudiences.value = currentAudiences.value.map((audience) =>
        audience.channel_id === data.channel_id ? data : audience,
      );

      // Revalidate funnel flow
      await paidSocialFormStore.revalidate();
    }

    async function createAudienceFromSaved(body: CreateAudienceFromSavedBody) {
      const { data } = await AudicenceApi.CreateAudienceFromSaved(body);

      if (currentAudiences.value.length === 0) {
        currentAudiences.value = [...currentAudiences.value, data];
      } else {
        currentAudiences.value = currentAudiences.value.map((audience) =>
          audience.channel_id === data.channel_id ? data : audience,
        );
      }

      // Revalidate funnel flow
      await paidSocialFormStore.revalidate();
    }

    async function cancelProposalAudiences(body: CancelProposalAudiencesBody) {
      await AudicenceApi.CancelProposalAudiences(body);
      currentAudiences.value = [];
    }

    function setContext({
      brand,
      campaign,
    }: {
      brand: number;
      campaign: number;
    }) {
      brandId.value = brand;
      campaignId.value = campaign;
    }

    // Check if the current ad set has any filled ads (ads with generated content)
    const selectedAdSetHasFilledAds = computed(() => {
      if (!selectedAdSet.value) return false;
      return paidSocialFormStore.adSetHasFilledAds(selectedAdSet.value.id);
    });

    return {
      brandId,
      campaignId,
      setContext,

      adSets,
      audiences: currentAudiences,
      savedAudiences,
      usedSavedAudiencesById,
      usedSavedAudiencesByName,
      getSavedAudienceUsage,
      selectedAdSet,
      selectedAdSetHasFilledAds,
      nextSet,

      loadAdSets,
      loadSavedAudiences,
      selectAdSet,
      generateAudiencesWithManualData,
      generateAudiencesFromDescriptionOrFile,
      saveAudience,
      unsaveAudience,
      deleteAudienceFromSaved,
      setPreferredAudience,
      updatePreferredAudience,
      createAudienceFromSaved,
      deleteAudience,
      cancelProposalAudiences,

      currentStep,
      setStep,
      openGenerateAudLoader,
      openSavedAudienceModal,
      startManual,
      closeAllModals,

      showAddSetModal,
      showSavedAudience,
      showCreateManual,
      showGenerateAudLoader,
      showGeneratedAudience,
      showEndMsg,
      showAddComment,
      showCancelAudience,
      showDeleteAudience,
      showEditAudience,
    };
  },
);
