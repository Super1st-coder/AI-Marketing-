<script setup lang="ts">
import AdStructureApi, {
  AdSetData,
  AdData,
} from "@/services/funnel-flow/paid-social/AdStructureApi";
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";

const { t } = useI18n();

const brandId = useBrandId();
const campaignId = useCampaignId();

const paidSocialFormStore = useFunnelPaidSocialFormStore();

const { data, goBack, goNext } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

const { data: initialData } = await AdStructureApi.getAdStructureByChannelGroup(
  brandId,
  campaignId,
  data.value.channelGroupId,
);

const adStructureId = initialData.id;
const adSets = ref(initialData.ad_sets);

const displayDeleteAdSetModal = ref(false);
const adSetToBeRemoved = ref<AdSetData | undefined>(undefined);

const handleDeleteAdSet = async (adSet: AdSetData) => {
  // Check if the Ad Set has dependencies
  if (paidSocialFormStore.adSetHasDependencies(adSet.id)) {
    // Show confirmation modal
    displayDeleteAdSetModal.value = true;
    adSetToBeRemoved.value = adSet;
  } else {
    // Happy Path - Delete immediately and silently
    adSetToBeRemoved.value = adSet;
    await handleDeleteAdSetConfirm();
  }
};

const handleDeleteAdSetCancel = async () => {
  displayDeleteAdSetModal.value = false;
  adSetToBeRemoved.value = undefined;
};

const handleDeleteAdSetConfirm = async () => {
  if (!adSetToBeRemoved.value?.id) {
    return;
  }

  try {
    displayDeleteAdSetModal.value = false;

    await AdStructureApi.deleteAdSet(
      brandId,
      campaignId,
      data.value.channelGroupId,
      adStructureId,
      adSetToBeRemoved.value.id,
    );

    // Update the local state by removing the ad set
    adSets.value = adSets.value.filter(
      (adSet) => adSet.id !== adSetToBeRemoved.value?.id,
    );

    // Revalidate funnel flow
    await paidSocialFormStore.revalidate();
  } catch (error) {
    console.error("Failed to delete ad set:", error);
  } finally {
    adSetToBeRemoved.value = undefined;
  }
};

const displayDeleteAdModal = ref(false);
const adToBeRemoved = ref<AdData | undefined>(undefined);
const adAdSetToBeRemoved = ref<AdSetData | undefined>(undefined);

// Get preview URL for an ad (first available format preview)
const adPreviewData = computed(() => {
  if (!adToBeRemoved.value?.id || !adAdSetToBeRemoved.value?.id)
    return undefined;

  const adData = paidSocialFormStore.getAdValidatorData(
    adAdSetToBeRemoved.value.id,
    adToBeRemoved.value.id,
  );
  if (!adData || adData.attributes.ad_channels.length === 0) return undefined;

  const channel = adData.attributes.ad_channels[0];
  if (!channel) return undefined;

  // Do not display preview if template_id is null
  if (!channel.media.template_id) return undefined;

  // Get the squarest image in the formats
  return {
    media: channel.media,
    channel_attributes: channel.channel_attributes,
  };
});

const handleDeleteAd = async (adSet: AdSetData, ad: AdData) => {
  // Check if the Ad is a filled slot
  if (paidSocialFormStore.isAdFilled(adSet.id, ad.id)) {
    // Show confirmation modal with preview
    displayDeleteAdModal.value = true;
    adAdSetToBeRemoved.value = adSet;
    adToBeRemoved.value = ad;
  } else {
    // Delete immediately and silently
    adAdSetToBeRemoved.value = adSet;
    adToBeRemoved.value = ad;
    await handleDeleteAdConfirm();
  }
};

const handleDeleteAdCancel = async () => {
  displayDeleteAdModal.value = false;
  adAdSetToBeRemoved.value = undefined;
  adToBeRemoved.value = undefined;
};

const handleDeleteAdConfirm = async () => {
  if (!adAdSetToBeRemoved.value?.id || !adToBeRemoved.value?.id) {
    return;
  }

  try {
    displayDeleteAdModal.value = false;

    await AdStructureApi.deleteAd(
      brandId,
      campaignId,
      data.value.channelGroupId,
      adStructureId,
      adAdSetToBeRemoved.value.id,
      adToBeRemoved.value.id,
    );

    // Update the local state by removing the ad from the specific ad set
    adSets.value = adSets.value.map((adSet) => ({
      ...adSet,
      ads: adSet.ads.filter((ad) => ad.id !== adToBeRemoved.value?.id),
    }));

    // Revalidate funnel flow
    await paidSocialFormStore.revalidate();
  } catch (error) {
    console.error("Failed to delete ad:", error);
  } finally {
    adAdSetToBeRemoved.value = undefined;
    adToBeRemoved.value = undefined;
  }
};

// Function to generate the next number based on existing items with names
const generateNextNumber = (items: { name: string }[]): number => {
  // Extract numbers from the end of each name
  const numbers = items
    .map((item) => {
      const match = item.name.match(/(\d+)$/);
      return match ? parseInt(match[1], 10) : 0;
    })
    .filter((num) => num > 0);

  // Find the maximum number, default to 0 if no numbers found
  const maxNumber = numbers.length > 0 ? Math.max(...numbers) : 0;

  // Return the next number
  return maxNumber + 1;
};

const isAddingAdToSetId = ref<undefined | number>(undefined);

const addAd = async (adSetId: number) => {
  isAddingAdToSetId.value = adSetId;

  try {
    const targetAdSet = adSets.value.find((adSet) => adSet.id === adSetId);
    if (!targetAdSet) {
      return;
    }

    // Get ads from the specific ad set to determine the next ad number
    const nextAdNumber = generateNextNumber(targetAdSet.ads);
    const newAdName = `Ad ${nextAdNumber}`;

    const response = await AdStructureApi.addAdToAdSet(
      brandId,
      campaignId,
      data.value.channelGroupId,
      adStructureId,
      adSetId,
      newAdName,
    );

    // Update the local state by creating a new array reference for reactivity
    adSets.value = adSets.value.map((adSet) =>
      adSet.id === adSetId
        ? {
            ...adSet,
            ads: [
              ...adSet.ads,
              {
                id: response.data.id,
                name: response.data.ad_name,
              },
            ],
          }
        : adSet,
    );

    // Revalidate funnel flow
    await paidSocialFormStore.revalidate();
  } catch (error) {
    console.error("Failed to add ad:", error);
  } finally {
    isAddingAdToSetId.value = undefined;
  }
};

const isAddingAdSet = ref(false);

// Edit Ad Set Name Modal
const isEditModalOpen = ref(false);
const editingAdSet = ref<AdSetData>();

const openEditModal = (adSet: AdSetData) => {
  editingAdSet.value = adSet;
  isEditModalOpen.value = true;
};

const handleAdSetNameSaved = ({ id, name }: { id: number; name: string }) => {
  adSets.value = adSets.value.map((adSet) =>
    adSet.id === id ? { ...adSet, name } : adSet,
  );
  editingAdSet.value = undefined;
};

const addAdSet = async () => {
  isAddingAdSet.value = true;

  try {
    // Generate the next ad set number based on existing ad sets
    const nextAdSetNumber = generateNextNumber(adSets.value);
    const newAdSetName = `Ad Set ${nextAdSetNumber}`;

    const response = await AdStructureApi.addAdSet(
      brandId,
      campaignId,
      data.value.channelGroupId,
      adStructureId,
      newAdSetName,
    );

    // Update the local state by creating a new array reference for reactivity
    adSets.value = [
      ...adSets.value,
      {
        id: response.data.id,
        name: response.data.ad_set_name,
        ads: [],
      },
    ];

    // Revalidate funnel flow
    await paidSocialFormStore.revalidate();
  } catch (error) {
    console.error("Failed to add ad set:", error);
  } finally {
    isAddingAdSet.value = false;
  }
};

const generalErrorMessage = ref<string | undefined>();

const validate = () => {
  if (adSets.value.length === 0) {
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.structure.new-structure.errors.at-least-one-ad-set",
    );
    return false;
  }

  if (!adSets.value.every((set) => set.ads.length > 0)) {
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.structure.new-structure.errors.at-least-one-ad-per-ad-set",
    );
    return false;
  }

  generalErrorMessage.value = undefined;
  return true;
};

watch(adSets, () => {
  if (generalErrorMessage.value) {
    validate();
  }
});

const handleSubmit = () => {
  if (validate()) {
    goNext();
  }
};
</script>

<template>
  <FormStepLayout as="div">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=js4olusGJ1I"
    >
      {{ $t("funnel-flow.paid-social.structure.new-structure.title") }}
    </PageTitle>

    <!-- Ad Sets Container -->
    <div class="tw:grid tw:grid-cols-1 tw:gap-6 tw:lg:grid-cols-3">
      <!-- Ad Sets -->
      <CardBase
        v-for="adSet in adSets"
        :key="adSet.id"
        class="tw:flex tw:flex-col tw:gap-6 tw:p-5"
        :class="{
          'tw:pointer-events-none tw:opacity-50':
            adSetToBeRemoved?.id === adSet.id,
        }"
      >
        <!-- Ad Set Header -->
        <div class="tw:flex tw:items-center tw:justify-between tw:gap-4">
          <div class="tw:flex tw:items-center tw:gap-2">
            <h3 class="tw:text-lg tw:font-extrabold">
              {{ adSet.name }}
            </h3>

            <button
              type="button"
              @click="openEditModal(adSet)"
              class="tw:flex tw:items-center tw:justify-center tw:text-gray-500 tw:hover:text-gray-700"
              :title="
                $t(
                  'funnel-flow.paid-social.structure.new-structure.tooltips.edit-ad-set-name',
                )
              "
            >
              <Icon icon="tabler-pencil" class="tw:text-xl" />
            </button>
          </div>

          <button
            type="button"
            @click="handleDeleteAdSet(adSet)"
            class="tw:flex tw:items-center tw:justify-center"
            :disabled="adSetToBeRemoved?.id === adSet.id"
          >
            <Icon icon="tabler-trash" class="tw:text-2xl" />
          </button>
        </div>

        <div
          v-for="ad in adSet.ads"
          :key="ad.id"
          class="tw:relative tw:flex tw:justify-center tw:rounded-lg tw:border-2 tw:border-input-border tw:p-4 tw:shadow-sm"
          :class="{
            'tw:pointer-events-none tw:opacity-50':
              adToBeRemoved?.id === ad.id &&
              adAdSetToBeRemoved?.id === adSet.id,
          }"
        >
          <span class="tw:font-bold tw:text-secondary">{{ ad.name }}</span>

          <button
            type="button"
            @click="handleDeleteAd(adSet, ad)"
            class="tw:absolute tw:top-0 tw:right-0 tw:translate-x-1/2 tw:-translate-y-1/2"
            :disabled="
              adToBeRemoved?.id === ad.id && adAdSetToBeRemoved?.id === adSet.id
            "
          >
            <Icon icon="tabler-circle-x-filled" class="tw:text-2xl" />
          </button>
        </div>

        <!-- Add New Ad Button -->
        <button
          type="button"
          @click="addAd(adSet.id)"
          class="tw:flex tw:items-center tw:justify-center tw:gap-2 tw:rounded-lg tw:border-2 tw:border-dashed tw:border-input-border tw:p-4"
          :class="{ 'tw:opacity-50': isAddingAdToSetId === adSet.id }"
          :disabled="isAddingAdToSetId === adSet.id"
        >
          <Icon icon="tabler-plus" class="tw:text-2xl" />
          <span class="tw:font-semibold">{{
            $t("funnel-flow.paid-social.structure.new-structure.actions.new-ad")
          }}</span>
        </button>
      </CardBase>

      <!-- Add New Ad Set Button -->
      <CardBase
        is="button"
        type="button"
        @click="addAdSet"
        class="tw:flex tw:min-h-40 tw:items-center tw:justify-center tw:gap-2 tw:self-start tw:bg-white/50 tw:p-6 tw:text-primary"
        :class="{ 'tw:opacity-50': isAddingAdSet }"
        :disabled="isAddingAdSet"
      >
        <Icon icon="tabler-plus" class="tw:text-2xl" />
        <span class="tw:text-base tw:leading-6 tw:font-semibold">
          {{
            $t(
              "funnel-flow.paid-social.structure.new-structure.actions.new-ad-set",
            )
          }}
        </span>
      </CardBase>
    </div>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="handleSubmit">
          {{
            $t(
              "funnel-flow.paid-social.structure.new-structure.actions.next-define-audience",
            )
          }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <!-- Delete ad -->
  <ModalGeneric
    v-model="displayDeleteAdModal"
    :maxWidth="660"
    @confirm="handleDeleteAdConfirm"
    @cancel="handleDeleteAdCancel"
    @close="handleDeleteAdCancel"
  >
    <template #title>
      {{
        $t("funnel-flow.paid-social.structure.new-structure.delete-ad.title")
      }}
    </template>

    <template v-if="adPreviewData" #before>
      <AdPreviewFromData
        :media="adPreviewData.media"
        :channel_attributes="adPreviewData.channel_attributes"
        class="tw:mb-4 tw:max-w-[300px]"
      />
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.structure.new-structure.delete-ad.description",
          { ad: adToBeRemoved?.name },
        )
      }}
    </template>

    <template #continue>
      {{
        $t("funnel-flow.paid-social.structure.new-structure.delete-ad.confirm")
      }}
    </template>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>
  </ModalGeneric>

  <!-- Delete ad set (Cascade Modal) -->
  <ModalGeneric
    v-model="displayDeleteAdSetModal"
    :maxWidth="660"
    @confirm="handleDeleteAdSetConfirm"
    @cancel="handleDeleteAdSetCancel"
    @close="handleDeleteAdSetCancel"
  >
    <template #title>
      {{
        $t(
          "funnel-flow.paid-social.structure.new-structure.delete-ad-set.title",
        )
      }}
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.structure.new-structure.delete-ad-set.description",
          {
            adSet: adSetToBeRemoved?.name,
          },
        )
      }}
    </template>

    <template #continue>
      {{
        $t(
          "funnel-flow.paid-social.structure.new-structure.delete-ad-set.confirm",
        )
      }}
    </template>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>
  </ModalGeneric>

  <!-- Edit Ad Set Name Modal -->
  <FunnelPaidSocialFormStructureEditModal
    v-if="editingAdSet && isEditModalOpen"
    v-model="isEditModalOpen"
    :channelGroupId="data.channelGroupId"
    :adStructureId="adStructureId"
    :adSet="editingAdSet"
    @saved="handleAdSetNameSaved"
  />
</template>
