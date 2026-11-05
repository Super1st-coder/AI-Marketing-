import { AdSetSidebar } from "@/components/funnel-flow/flows/paid-social/FunnelPaidSocialFormSideBar.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import AdsExperiment, {
  AdsExperimentByAdSetData,
  AdsExperimentType,
} from "@/services/funnel-flow/paid-social/AdsExperiment";

export const useFunnelPaidSocialExperimentStore = defineStore(
  "FunnelPaidSocialExperimentStore",
  () => {
    const brandId = ref<number | undefined>(undefined);
    const campaignId = ref<number | undefined>(undefined);
    const channelGroupId = ref<number>(0);

    const adSets = ref<AdSetSidebar[]>([]);
    const selectedAdSetIndex = ref<number>(0);
    const selectedAdSet = computed(
      () => adSets.value[selectedAdSetIndex.value],
    );
    const nextSet = computed(() =>
      adSets.value.find(
        (set) => set.hasAlert && set.id !== selectedAdSet.value?.id,
      ),
    );

    const allExperiments = ref<(AdsExperimentByAdSetData | undefined)[]>([]);
    const currentExperiment = computed(
      () => allExperiments.value[selectedAdSetIndex.value],
    );

    // Reference to the main form store
    const formStore = useFunnelPaidSocialFormStore();

    // Check if an experiment is complete (has type and subcategory set)
    function isExperimentComplete(
      experiment: AdsExperimentByAdSetData | undefined,
    ): boolean {
      if (!experiment) return false;
      return !!experiment.type && !!experiment.subcategory?.id;
    }

    // Update hasAlert flags based on experiment completion
    watch(
      allExperiments,
      (experiments) => {
        adSets.value = adSets.value.map((set, index) => ({
          ...set,
          hasAlert: !isExperimentComplete(experiments[index]),
        }));
      },
      { immediate: true, deep: true },
    );

    async function initialize({
      brand,
      campaign,
      channelGroupId,
    }: {
      brand: number;
      campaign: number;
      channelGroupId: number;
    }) {
      brandId.value = brand;
      campaignId.value = campaign;
      await loadAdSets(channelGroupId);
    }

    async function loadAdSets(_channelGroupId: number) {
      channelGroupId.value = _channelGroupId;

      if (brandId.value == null || campaignId.value == null) {
        throw new Error("Call initialize first");
      }

      // Fetch ad structure
      const { data } = await AdStructureApi.getAdStructureByChannelGroup(
        brandId.value,
        campaignId.value,
        channelGroupId.value,
      );

      // Fetch experiments for all adsets
      allExperiments.value = await Promise.all(
        data.ad_sets.map(async (set) => {
          try {
            const response = await AdsExperiment.getExperimentByAdSet(
              brandId.value!,
              campaignId.value!,
              set.id,
            );

            return response.data;
          } catch (e: unknown) {
            console.error(e);
            return undefined;
          }
        }),
      );

      // Save the structure with hasAlert flags
      adSets.value = data.ad_sets.map((set, index) => ({
        ...set,
        open: false,
        hasAlert: !isExperimentComplete(allExperiments.value[index]),
      }));

      // Select the first adset
      if (adSets.value.length) {
        moveToAdSet(adSets.value[0].id);
      }
    }

    function moveToAdSet(adSetId: number) {
      const index = adSets.value.findIndex((set) => set.id === adSetId);
      if (index !== -1) {
        selectedAdSetIndex.value = index;
      }
    }

    async function refetchCurrentExperiment() {
      if (brandId.value == null || campaignId.value == null) {
        throw new Error("Store not initialized");
      }

      if (!selectedAdSet.value) {
        throw new Error("No ad set selected");
      }

      // Fetch the updated experiment to get the full data structure
      const experimentResponse = await AdsExperiment.getExperimentByAdSet(
        brandId.value,
        campaignId.value,
        selectedAdSet.value.id,
      );

      // Update the current experiment in the store
      if (experimentResponse.data) {
        allExperiments.value[selectedAdSetIndex.value] =
          experimentResponse.data;
      }

      return experimentResponse;
    }

    async function defineCurrentExperiment(
      subcategoryId: number,
      type: AdsExperimentType,
    ) {
      if (brandId.value == null || campaignId.value == null) {
        throw new Error("Store not initialized");
      }

      if (!selectedAdSet.value) {
        throw new Error("No ad set selected");
      }

      // Check if experiment already exists (editing mode)
      const existingExperiment = currentExperiment.value;
      let response;

      if (existingExperiment?.id) {
        // Update existing experiment
        response = await AdsExperiment.updateExperimentByAdSet(
          brandId.value,
          campaignId.value,
          existingExperiment.id,
          selectedAdSet.value.id,
          subcategoryId,
          type,
        );
      } else {
        // Create new experiment
        response = await AdsExperiment.defineExperimentByAdSet(
          brandId.value,
          campaignId.value,
          selectedAdSet.value.id,
          subcategoryId,
          type,
        );
      }

      // Refetch the current experiment to update the store
      await refetchCurrentExperiment();

      // Revalidate the main form store
      await formStore.revalidate();

      return response;
    }

    async function deleteCurrentExperiment() {
      if (brandId.value == null || campaignId.value == null) {
        throw new Error("Store not initialized");
      }

      if (!currentExperiment.value?.id) {
        throw new Error("No experiment to delete");
      }

      await AdsExperiment.deleteExperimentByAdSet(
        brandId.value,
        campaignId.value,
        selectedAdSet.value.id,
        currentExperiment.value.id,
      );

      // Clear the experiment from the store
      allExperiments.value[selectedAdSetIndex.value] = undefined;

      // Revalidate the main form store
      await formStore.revalidate();
    }

    return {
      brandId,
      campaignId,
      channelGroupId,
      initialize,

      adSets,
      selectedAdSet,
      selectedAdSetIndex,
      nextSet,

      allExperiments,
      currentExperiment,

      loadAdSets,
      selectAdSet: moveToAdSet,
      refetchCurrentExperiment,
      defineCurrentExperiment,
      deleteCurrentExperiment,
      isExperimentComplete,
    };
  },
);
