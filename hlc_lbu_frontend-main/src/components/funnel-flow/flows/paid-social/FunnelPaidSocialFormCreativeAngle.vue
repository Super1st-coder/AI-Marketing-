<script setup lang="ts">
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";
import FunnelPaidSocialFormSideBar, {
  type AdSetSidebar,
} from "./FunnelPaidSocialFormSideBar.vue";
import type { AdsExperimentByAdSetData } from "@/services/funnel-flow/paid-social/AdsExperiment";

const { data, goNext, goBack } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();

const formStore = useFunnelPaidSocialFormStore();
const store = useFunnelPaidSocialExperimentStore();
await store.initialize({
  brand: brandId,
  campaign: campaignId,
  channelGroupId: data.value.channelGroupId,
});

const { t } = useI18n();

const sidebar = ref<InstanceType<typeof FunnelPaidSocialFormSideBar>>();
const isModalOpen = ref(false);
const editingExperiment = ref<AdsExperimentByAdSetData | undefined>(undefined);
const isEndMessageModalOpen = ref(false);
const isDeleteModalOpen = ref(false);

function navigateBack() {
  const firstAdset = store.adSets[0];
  if (firstAdset?.id === sidebar.value?.getSelectedAdSetId()) {
    goBack();
  } else {
    sidebar.value?.goPrev();
  }
}

function handleSelectAdSet(adSetId: number) {
  store.selectAdSet(adSetId);
}

function handleOpenModal() {
  editingExperiment.value = undefined;
  isModalOpen.value = true;
}

function handleEditExperiment() {
  editingExperiment.value = store.currentExperiment;
  isModalOpen.value = true;
}

async function handleDeleteExperiment() {
  if (!store.selectedAdSet?.id) return;

  // No filled ads - delete immediately and silently
  if (!formStore.adSetHasFilledAds(store.selectedAdSet.id)) {
    await store.deleteCurrentExperiment();
    return;
  }

  // Has filled ads - show confirm modal
  isDeleteModalOpen.value = true;
}

const generalErrorMessage = ref<string | undefined>();
const validate = () => {
  if (!store.isExperimentComplete(store.currentExperiment)) {
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.creative-angle.errors.must-define-creative-angle",
    );
    return false;
  }

  generalErrorMessage.value = undefined;
  return true;
};

async function handleNext() {
  if (validate()) {
    await formStore.revalidate();
    isEndMessageModalOpen.value = true;
  }
}

function closeEndMessageModal() {
  isEndMessageModalOpen.value = false;
}

function navigateToAdSet(nextAdset: AdSetSidebar) {
  store.selectAdSet(nextAdset.id);
  sidebar.value?.goToAdSetId(nextAdset.id);
  closeEndMessageModal();
}

function handleGoNext() {
  goNext();
  closeEndMessageModal();
}
</script>

<template>
  <FunnelPaidSocialFormSideBar
    ref="sidebar"
    :title="data.campaign.name"
    :adSets="store.adSets"
    :adsClickeables="false"
    @selectAdSet="handleSelectAdSet"
  >
    <FormStepLayout as="div">
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=S8XpKvlswXY"
      >
        {{ $t("funnel-flow.paid-social.creative-angle.title") }}
      </PageTitle>

      <CardBase
        v-if="store.currentExperiment"
        class="tw:mx-auto tw:w-full tw:max-w-[974px]"
      >
        <!-- Header -->
        <div class="tw:flex tw:items-center tw:justify-between tw:px-6 tw:py-5">
          <h2 class="tw:text-xl tw:font-bold">
            {{
              $te(
                `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(store.currentExperiment.subcategory.name)}.name`,
              )
                ? $t(
                    `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(store.currentExperiment.subcategory.name)}.name`,
                  )
                : store.currentExperiment.subcategory.name
            }}
          </h2>

          <ButtonDropdownIcon placement="bottom-start" icon="tabler-dots">
            <template #options>
              <ButtonDropdownOption
                leftIcon="tabler-pencil"
                @click="handleEditExperiment"
              >
                {{
                  $t("funnel-flow.paid-social.creative-angle.main.edit-button")
                }}
              </ButtonDropdownOption>

              <ButtonDropdownOption
                leftIcon="tabler-trash"
                class="tw:text-error!"
                @click="handleDeleteExperiment"
              >
                {{
                  $t(
                    "funnel-flow.paid-social.creative-angle.main.delete-button",
                  )
                }}
              </ButtonDropdownOption>
            </template>
          </ButtonDropdownIcon>
        </div>

        <Separator />

        <!-- Content -->
        <CreativeAnglePreview
          :creativeAngle="store.currentExperiment"
          class="tw:p-6"
        />
      </CardBase>
      <CardBase v-else class="tw:mx-auto tw:w-full tw:max-w-[500px]">
        <div class="tw:p-6">
          <h2 class="tw:text-xl tw:font-extrabold">
            {{
              $t(
                "funnel-flow.paid-social.creative-angle.main.set-creative-angle-title",
                { adSetName: store.selectedAdSet.name },
              )
            }}
          </h2>
        </div>

        <Separator />

        <div class="tw:p-6">
          <h3 class="tw:mb-1 tw:text-xl tw:font-extrabold">
            {{
              $t(
                "funnel-flow.paid-social.creative-angle.main.missing-strategy-title",
              )
            }}
          </h3>

          <p class="tw:mb-6 tw:text-secondary-text">
            {{
              $t(
                "funnel-flow.paid-social.creative-angle.main.missing-strategy-description",
              )
            }}
          </p>

          <Button size="md" type="button" @click="handleOpenModal">
            {{
              $t(
                "funnel-flow.paid-social.creative-angle.main.define-creative-angle-button",
              )
            }}
          </Button>
        </div>
      </CardBase>

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}
      </Alert>

      <!-- End Msg -->
      <CreativeAngleEndMessageModal
        v-model="isEndMessageModalOpen"
        :nextSet="store.nextSet"
        :selectedAdSet="store.selectedAdSet"
        @navigateToAdSet="navigateToAdSet"
        @goNext="handleGoNext"
      />

      <template #actions>
        <WizardCardActions>
          <ButtonGoBack @click="navigateBack()" />
          <ButtonNext type="button" @click="handleNext()" />
        </WizardCardActions>
      </template>
    </FormStepLayout>

    <CreativeAngleModal v-model="isModalOpen" :experiment="editingExperiment" />

    <CreativeAngleDeleteModal v-model="isDeleteModalOpen" />
  </FunnelPaidSocialFormSideBar>
</template>
